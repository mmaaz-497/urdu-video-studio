import uuid

from fastapi import Cookie, Request, Response

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.redis_client import call_with_timeout, get_redis

SESSION_COOKIE_NAME = "session_id"
_SESSION_KEY_PREFIX = "session:"


def _session_key(session_id: str) -> str:
    return f"{_SESSION_KEY_PREFIX}{session_id}"


async def create_session(student_id: uuid.UUID | str) -> str:
    settings = get_settings()
    session_id = uuid.uuid4().hex
    await call_with_timeout(
        get_redis().set(_session_key(session_id), str(student_id), ex=settings.SESSION_TTL_SECONDS),
        error_code="SESSION_STORE_UNAVAILABLE",
        message="Could not start your session. Please try again.",
    )
    return session_id


async def get_session(session_id: str) -> str | None:
    return await call_with_timeout(
        get_redis().get(_session_key(session_id)),
        error_code="SESSION_STORE_UNAVAILABLE",
        message="Could not verify your session. Please try again.",
    )


async def destroy_session(session_id: str) -> None:
    await call_with_timeout(
        get_redis().delete(_session_key(session_id)),
        error_code="SESSION_STORE_UNAVAILABLE",
        message="Could not end your session. Please try again.",
    )


def set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


async def require_session(
    request: Request,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> uuid.UUID:
    """FastAPI dependency: resolves the session cookie to a student id, or 401s."""
    if session_id is None:
        raise AppError("UNAUTHENTICATED", "Please log in to continue.")

    student_id = await get_session(session_id)
    if student_id is None:
        raise AppError("UNAUTHENTICATED", "Your session has expired. Please log in again.")

    request.state.session_id = session_id
    return uuid.UUID(student_id)
