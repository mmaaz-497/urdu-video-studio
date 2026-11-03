import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_var

logger = get_logger(__name__)

_STATUS_BY_CODE: dict[str, int] = {
    "DATABASE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "CACHE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "SESSION_STORE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "STORAGE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "EMAIL_SEND_FAILED": status.HTTP_503_SERVICE_UNAVAILABLE,
    "RUNPOD_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "MODERATION_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "UNSAFE_CONTENT": status.HTTP_400_BAD_REQUEST,
    "SCRIPT_GENERATION_FAILED": status.HTTP_502_BAD_GATEWAY,
    "SCRIPT_TOO_LONG": status.HTTP_400_BAD_REQUEST,
    "ASSEMBLY_FAILED": status.HTTP_502_BAD_GATEWAY,
    "DAILY_VIDEO_LIMIT_REACHED": status.HTTP_429_TOO_MANY_REQUESTS,
    "DAILY_SCRIPT_LIMIT_REACHED": status.HTTP_429_TOO_MANY_REQUESTS,
    "REQUEST_IN_PROGRESS": status.HTTP_425_TOO_EARLY,
    "DELETE_WHILE_PROCESSING": status.HTTP_409_CONFLICT,
    "RETRY_NOT_ALLOWED": status.HTTP_409_CONFLICT,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "UNAUTHENTICATED": status.HTTP_401_UNAUTHORIZED,
    "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
    "EMAIL_ALREADY_REGISTERED": status.HTTP_409_CONFLICT,
    "CSRF_FAILED": status.HTTP_403_FORBIDDEN,
    "INVALID_RESET_TOKEN": status.HTTP_400_BAD_REQUEST,
    "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_CONTENT,
}

_DEFAULT_MESSAGE = "Something went wrong. Please try again."


class AppError(Exception):
    """Base error for every friendly, client-facing failure.

    `message` is always safe to show to a student; any underlying exception
    detail is logged server-side (T017) and never included in the response.
    """

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        status_code: int | None = None,
        extra: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message or _DEFAULT_MESSAGE
        self.status_code = status_code or _STATUS_BY_CODE.get(
            code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.extra = extra or {}
        super().__init__(f"{code}: {self.message}")


def _error_body(code: str, message: str, request_id: str, extra: dict | None = None) -> dict:
    body = {"error": {"code": code, "message": message, "requestId": request_id}}
    if extra:
        body["error"].update(extra)
    return body


def _get_request_id(request: Request) -> str:
    return request_id_var.get() or getattr(request.state, "request_id", None) or str(uuid.uuid4())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning(
            "app_error",
            extra={"code": exc.code, "error_message": exc.message, "request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, request_id, exc.extra),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body("VALIDATION_ERROR", "The request data is invalid.", request_id),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.exception("unhandled_exception", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", _DEFAULT_MESSAGE, request_id),
        )
