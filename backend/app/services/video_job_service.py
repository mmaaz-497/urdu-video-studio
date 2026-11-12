import base64
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.video_job import VideoJob
from app.schemas.scripts import Scene
from app.schemas.videos import CreateVideoJobRequest
from app.services import usage_service

_TERMINAL_STATUSES = ("ready", "failed")
_DEFAULT_PAGE_SIZE = 20


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

    # Imported here, not at module level: llm_service pulls in the OpenAI Agents SDK
    # (~100 MB), and the scheduler imports this module only for mark_status().
    from app.services import llm_service

    scene_count = payload.durationSeconds // 5
    if len(payload.scenes) != scene_count:
        raise AppError("VALIDATION_ERROR", f"Exactly {scene_count} scene(s) are required.")
    for scene in payload.scenes:
        words = llm_service.word_count(scene.narrationUr)
        if words == 0 or not scene.visualPrompt.strip():
            raise AppError(
                "VALIDATION_ERROR", "Every scene needs a visual prompt and a narration."
            )
        if words > llm_service.WORDS_PER_5S_MAX:
            raise AppError(
                "SCRIPT_TOO_LONG",
                "Script is too long for the chosen duration — please shorten it",
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
        urdu_script=" ".join(s.narrationUr.strip() for s in payload.scenes),
        scenes=[s.model_dump() for s in payload.scenes],
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


def scenes_of(job: VideoJob) -> list[Scene]:
    """Typed scenes of a job. Rows from before per-scene narration hold plain strings (a
    visual prompt only); they are read with an empty narration and cannot be retried."""
    return [
        Scene(visualPrompt=s, narrationUr="") if isinstance(s, str) else Scene(**s)
        for s in job.scenes
    ]


def get_job(db: Session, job_id: uuid.UUID) -> VideoJob | None:
    return db.get(VideoJob, job_id)


def _encode_cursor(job: VideoJob) -> str:
    raw = f"{job.created_at.isoformat()}|{job.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_str, id_str = raw.split("|", 1)
        return datetime.fromisoformat(created_at_str), uuid.UUID(id_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError("VALIDATION_ERROR", "Invalid pagination cursor.") from exc


def list_for_student(
    db: Session, student_id: uuid.UUID, cursor: str | None = None, limit: int = _DEFAULT_PAGE_SIZE
) -> tuple[list[VideoJob], str | None]:
    """Newest-first, cursor-paginated. Returns (jobs, nextCursor) where
    `nextCursor` is None once there are no more pages."""
    stmt = select(VideoJob).where(VideoJob.student_id == student_id)
    if cursor:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                VideoJob.created_at < cursor_created_at,
                and_(VideoJob.created_at == cursor_created_at, VideoJob.id < cursor_id),
            )
        )
    stmt = stmt.order_by(VideoJob.created_at.desc(), VideoJob.id.desc()).limit(limit + 1)
    jobs = list(db.execute(stmt).scalars().all())
    has_more = len(jobs) > limit
    jobs = jobs[:limit]
    next_cursor = _encode_cursor(jobs[-1]) if has_more and jobs else None
    return jobs, next_cursor


def delete(db: Session, job: VideoJob) -> None:
    if job.status not in _TERMINAL_STATUSES:
        raise AppError(
            "DELETE_WHILE_PROCESSING",
            "This video is still being created — please wait until it's ready or failed "
            "before deleting it.",
        )
    db.delete(job)
    db.commit()


def retry(db: Session, job: VideoJob) -> tuple[VideoJob, bool]:
    if job.status != "failed":
        raise AppError("RETRY_NOT_ALLOWED", "Only failed videos can be retried.")
    scenes = scenes_of(job)
    if any(not s.narrationUr.strip() for s in scenes):
        raise AppError(
            "RETRY_NOT_ALLOWED",
            "This video was made with an older version and can't be retried. "
            "Please create a new one.",
        )
    payload = CreateVideoJobRequest(
        idempotencyKey=uuid.uuid4(),
        correctedIdea=job.corrected_idea,
        title=job.title,
        urduScript=job.urdu_script,
        scenes=scenes,
        durationSeconds=job.duration_seconds,
        aspectRatio=job.aspect_ratio,
        voiceId=job.voice_id,
    )
    return create_job(db, job.student_id, payload)


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
