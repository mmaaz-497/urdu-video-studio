from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    requestId: str | None = None
    resetsAt: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
