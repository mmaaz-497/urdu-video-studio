import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.models.video_job import VideoJob
from app.services import usage_service, video_job_service

logger = get_logger(__name__)

NON_TERMINAL_STATUSES = ("queued", "preparing", "generating_scenes", "adding_voice", "finalizing")
SWEEP_INTERVAL_SECONDS = 30
STALE_FAILURE_REASON = "This took too long — please try again"


def sweep_once() -> int:
    """Marks every non-terminal VideoJob older than MAX_PROCESSING_SECONDS as
    failed, decrementing its daily-usage claim (research.md A7). Returns the
    number of jobs swept."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.MAX_PROCESSING_SECONDS)
    db = SessionLocal()
    swept = 0
    try:
        stale_jobs = (
            db.execute(
                select(VideoJob).where(
                    VideoJob.status.in_(NON_TERMINAL_STATUSES), VideoJob.created_at < cutoff
                )
            )
            .scalars()
            .all()
        )
        for job in stale_jobs:
            video_job_service.mark_status(
                db, job.id, "failed", failure_reason=STALE_FAILURE_REASON
            )
            usage_service.decrement_video_count(db, job.student_id)
            db.commit()
            swept += 1
            logger.warning("stale_job_marked_failed", extra={"job_id": str(job.id)})
    finally:
        db.close()
    return swept


def main() -> None:
    configure_logging()
    logger.info("scheduler_started", extra={"interval_seconds": SWEEP_INTERVAL_SECONDS})
    while True:
        try:
            sweep_once()
        except Exception:
            logger.exception("scheduler_sweep_failed")
        time.sleep(SWEEP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
