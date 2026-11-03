import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.video_job import VideoJob
from app.schemas.videos import CreateVideoJobRequest
from app.services import llm_service, usage_service

_TERMINAL_STATUSES = ("ready", "failed")


def create_job(
    db: Session, student_id: uuid.UUID, payload: CreateVideoJobRequest
) -> tuple[VideoJob, bool]:
    """Returns (job, created). `created=False` means an existing job for this
    (student, idempotencyKey) was returned instead of creating a duplicate
    (research.md A3)."""
    existing = db.execute(
        select(VideoJob).where(
            VideoJob.student_id == student_id,
            VideoJob.idempotency_key == str(payload.idempotencyKey),
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    scene_count = payload.durationSeconds // 5
    word_too_long = (
        len(payload.scenes) != scene_count
        or llm_service.word_count(payload.urduScript) > llm_service.word_limit_for(
            payload.durationSeconds
        )
    )
    if word_too_long:
        raise AppError(
            "SCRIPT_TOO_LONG", "Script is too long for the chosen duration — please shorten it"
        )

    if not usage_service.try_increment_video_count(db, student_id):
        db.commit()
        raise AppError(
            "DAILY_VIDEO_LIMIT_REACHED",
            "You've used all your videos for today. Come back after midnight "
            "(Asia/Karachi) for more.",
            extra={"resetsAt": usage_service.resets_at().isoformat()},
        )

    job = VideoJob(
        student_id=student_id,
        idempotency_key=str(payload.idempotencyKey),
        raw_idea=payload.correctedIdea,
        corrected_idea=payload.correctedIdea,
        title=payload.title,
        urdu_script=payload.urduScript,
        scenes=payload.scenes,
        duration_seconds=payload.durationSeconds,
        aspect_ratio=payload.aspectRatio,
        voice_id=payload.voiceId,
        status="queued",
        progress_total_scenes=scene_count,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, True


def get_job(db: Session, job_id: uuid.UUID) -> VideoJob | None:
    return db.get(VideoJob, job_id)


def mark_status(db: Session, job_id: uuid.UUID, status: str, **fields) -> VideoJob | None:
    job = db.get(VideoJob, job_id)
    if job is None:
        return None
    job.status = status
    for key, value in fields.items():
        setattr(job, key, value)
    if status in _TERMINAL_STATUSES:
        job.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job
