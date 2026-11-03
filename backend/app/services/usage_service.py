import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.usage_counter import UsageCounter

KARACHI_TZ = ZoneInfo("Asia/Karachi")


def _today() -> date:
    return datetime.now(KARACHI_TZ).date()


def _resets_at() -> datetime:
    tomorrow = _today() + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=KARACHI_TZ)


def _get_or_create_counter(
    db: Session, student_id: uuid.UUID, *, for_update: bool = False
) -> UsageCounter:
    today = _today()
    stmt = select(UsageCounter).where(
        UsageCounter.student_id == student_id, UsageCounter.usage_date == today
    )
    if for_update:
        stmt = stmt.with_for_update()
    counter = db.execute(stmt).scalar_one_or_none()
    if counter is None:
        counter = UsageCounter(
            student_id=student_id, usage_date=today, video_count=0, script_count=0
        )
        db.add(counter)
        db.flush()
    return counter


def get_usage_summary(db: Session, student_id: uuid.UUID) -> dict:
    """Read-only summary for GET /me."""
    settings = get_settings()
    counter = _get_or_create_counter(db, student_id)
    return {
        "videosUsedToday": counter.video_count,
        "videoLimit": settings.DAILY_VIDEO_LIMIT,
        "scriptsUsedToday": counter.script_count,
        "scriptLimit": settings.DAILY_SCRIPT_LIMIT,
        "resetsAt": _resets_at(),
    }


def increment_script_count(db: Session, student_id: uuid.UUID) -> None:
    """Unconditionally increments under the day's row lock. Caller enforces DAILY_SCRIPT_LIMIT."""
    counter = _get_or_create_counter(db, student_id, for_update=True)
    counter.script_count += 1
    db.flush()


def try_increment_video_count(db: Session, student_id: uuid.UUID) -> bool:
    """Atomically claims one video slot for today. Returns False if DAILY_VIDEO_LIMIT is reached."""
    settings = get_settings()
    counter = _get_or_create_counter(db, student_id, for_update=True)
    if counter.video_count >= settings.DAILY_VIDEO_LIMIT:
        return False
    counter.video_count += 1
    db.flush()
    return True


def decrement_video_count(db: Session, student_id: uuid.UUID) -> None:
    """Reverses a claimed video slot (floor 0) for a job that failed for a
    reason excluded from the limit."""
    counter = _get_or_create_counter(db, student_id, for_update=True)
    counter.video_count = max(0, counter.video_count - 1)
    db.flush()
