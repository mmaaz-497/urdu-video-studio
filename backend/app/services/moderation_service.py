import asyncio

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

MODERATION_TIMEOUT_SECONDS = 10.0
MAX_ATTEMPTS = 2  # one call + one retry

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=get_settings().OPENAI_API_KEY)
    return _client


async def check_idea(idea: str) -> None:
    """Raises AppError('UNSAFE_CONTENT') if the moderation endpoint flags the
    idea, or AppError('MODERATION_UNAVAILABLE') if the call fails after one
    retry (FR-008)."""
    client = _get_client()
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await asyncio.wait_for(
                client.moderations.create(input=idea), timeout=MODERATION_TIMEOUT_SECONDS
            )
            if result.results[0].flagged:
                raise AppError(
                    "UNSAFE_CONTENT", "This idea can't be used. Please choose a different topic."
                )
            return
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001 - any client/timeout error, retried once
            last_exc = exc
            logger.warning(
                "moderation_call_failed", extra={"attempt": attempt, "max_attempts": MAX_ATTEMPTS}
            )

    logger.error("moderation_unavailable", exc_info=last_exc)
    raise AppError(
        "MODERATION_UNAVAILABLE", "Content check is temporarily unavailable. Please try again."
    )
