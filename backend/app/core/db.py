import time
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


_settings = get_settings()

engine = create_engine(
    _settings.DATABASE_URL,
    connect_args={"connect_timeout": 5},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def connect_with_retry(max_attempts: int = 3, base_delay_seconds: float = 0.5) -> None:
    """Verify DB connectivity at startup, retrying with backoff before failing loud."""
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect():
                return
        except Exception as exc:  # noqa: BLE001 - re-raised as AppError below
            last_exc = exc
            logger.warning(
                "db_connect_retry",
                extra={"attempt": attempt, "max_attempts": max_attempts},
            )
            if attempt < max_attempts:
                time.sleep(base_delay_seconds * attempt)
    logger.error("db_connect_exhausted", exc_info=last_exc)
    raise AppError(
        "DATABASE_UNAVAILABLE", "The database is temporarily unavailable. Please try again shortly."
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
