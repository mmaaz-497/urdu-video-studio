import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.core.config import get_settings
from app.core.db import connect_with_retry
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger, request_id_var
from app.core.redis_client import close_redis
from app.services.storage_local import STATIC_MOUNT_PATH

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    connect_with_retry()
    yield
    await close_redis()


app = FastAPI(title="Urdu Video Studio API", version="1.0.0", lifespan=lifespan)

# Same-origin only: the frontend proxies /api/* to this backend (T031a dev,
# Caddy in prod), so session/CSRF cookies are first-party and no CORS
# middleware is needed for cross-origin credentialed requests.

register_exception_handlers(app)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-Id"] = request_id
    return response


settings = get_settings()
if settings.STORAGE_PROVIDER == "local":
    Path(settings.LOCAL_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    app.mount(STATIC_MOUNT_PATH, StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="static")

app.include_router(auth_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
