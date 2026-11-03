import asyncio
from collections.abc import Awaitable, Coroutine

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

REDIS_CALL_TIMEOUT_SECONDS = 2.0

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Shared redis.asyncio connection pool, built once from REDIS_URL per event loop."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Closes and clears the shared client so the next get_redis() rebinds to the current loop.

    Needed because redis.asyncio.Redis pins its connections to the event loop
    active when they were opened — a new loop per app lifespan (every test's
    TestClient, or a real process restart) must get a fresh client.
    """
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def call_with_timeout[T](
    awaitable: Coroutine[None, None, T] | Awaitable[T],
    *,
    error_code: str = "CACHE_UNAVAILABLE",
    message: str = "A temporary service is unavailable. Please try again.",
) -> T:
    """Wrap any Redis call with a 2s timeout and a friendly AppError on failure."""
    try:
        return await asyncio.wait_for(awaitable, timeout=REDIS_CALL_TIMEOUT_SECONDS)
    except (TimeoutError, redis.RedisError) as exc:
        logger.error("redis_call_failed", exc_info=exc)
        raise AppError(error_code, message) from exc
