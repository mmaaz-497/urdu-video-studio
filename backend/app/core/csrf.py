import secrets

from fastapi import Header, Request, Response

from app.core.config import get_settings
from app.core.errors import AppError

_CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def issue_csrf_cookie(response: Response) -> str:
    """Sets a non-httpOnly, SameSite=Lax CSRF cookie alongside the session cookie."""
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return token


async def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    """Double-submit CSRF check for any state-changing request."""
    if request.method not in _CSRF_PROTECTED_METHODS:
        return

    settings = get_settings()
    cookie_value = request.cookies.get(settings.CSRF_COOKIE_NAME)
    if (
        not cookie_value
        or not x_csrf_token
        or not secrets.compare_digest(cookie_value, x_csrf_token)
    ):
        raise AppError(
            "CSRF_FAILED", "Your session could not be verified. Please refresh and try again."
        )
