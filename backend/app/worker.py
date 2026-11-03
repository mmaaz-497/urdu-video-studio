import redis
from rq import Queue, Worker

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

QUEUE_NAME = "videos"

logger = get_logger(__name__)

_queue: Queue | None = None


def _connection() -> redis.Redis:
    return redis.Redis.from_url(get_settings().REDIS_URL)


def get_queue() -> Queue:
    """Shared sync (non-asyncio) Redis-backed RQ queue — RQ's producer/consumer
    API is synchronous, unlike the rest of the app's asyncio Redis client."""
    global _queue
    if _queue is None:
        _queue = Queue(QUEUE_NAME, connection=_connection())
    return _queue


def main() -> None:
    configure_logging()
    logger.info("worker_started", extra={"queue": QUEUE_NAME})
    worker = Worker([QUEUE_NAME], connection=_connection())
    worker.work()


if __name__ == "__main__":
    main()
