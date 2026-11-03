import asyncio
import tempfile
import time
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.core.logging import get_logger
from app.services import ffmpeg_service, mock_provider, usage_service, video_job_service
from app.services.storage_service import get_storage

logger = get_logger(__name__)

# Simulated per-step delay in mock mode, so the progress UI visibly moves
# through Preparing -> Generating scenes -> Adding voice -> Finalizing.
MOCK_STEP_DELAY_SECONDS = 1.0


def _upload(key: str, data: bytes, content_type: str) -> None:
    storage = get_storage()
    asyncio.run(storage.upload(key, data, content_type))


def run_job(job_id: str) -> None:
    """RQ job entrypoint. Opens its own DB session (runs in the worker
    process, not a request-scoped FastAPI dependency)."""
    db = SessionLocal()
    try:
        job = video_job_service.get_job(db, uuid.UUID(job_id))
        if job is None:
            logger.warning("video_job_not_found", extra={"job_id": job_id})
            return

        try:
            settings = get_settings()
            if settings.VIDEO_PROVIDER != "mock":
                raise AppError(
                    "RUNPOD_UNAVAILABLE",
                    "Real video generation isn't available yet. Please try again later.",
                )
            _run_mock(db, job)
        except AppError as exc:
            logger.warning("video_job_failed", extra={"job_id": job_id, "code": exc.code})
            video_job_service.mark_status(db, job.id, "failed", failure_reason=exc.message)
            usage_service.decrement_video_count(db, job.student_id)
            db.commit()
        except Exception:
            logger.exception("video_job_unexpected_error", extra={"job_id": job_id})
            video_job_service.mark_status(
                db,
                job.id,
                "failed",
                failure_reason="Something went wrong while creating your video. Please try again.",
            )
            usage_service.decrement_video_count(db, job.student_id)
            db.commit()
    finally:
        db.close()


def _run_mock(db, job) -> None:
    scene_count = job.progress_total_scenes

    video_job_service.mark_status(db, job.id, "preparing")
    assets = mock_provider.pick_assets(job.aspect_ratio, scene_count, job.voice_id)

    video_job_service.mark_status(db, job.id, "generating_scenes", progress_current_scene=0)
    for i in range(1, scene_count + 1):
        time.sleep(MOCK_STEP_DELAY_SECONDS)
        video_job_service.mark_status(db, job.id, "generating_scenes", progress_current_scene=i)

    video_job_service.mark_status(db, job.id, "adding_voice")
    time.sleep(MOCK_STEP_DELAY_SECONDS)

    video_job_service.mark_status(db, job.id, "finalizing")
    with tempfile.TemporaryDirectory(prefix=f"job-{job.id}-") as tmp:
        tmp_path = Path(tmp)
        concat_path = str(tmp_path / "concat.mp4")
        narrated_path = str(tmp_path / "narrated.mp4")
        final_path = str(tmp_path / "final.mp4")
        thumb_path = str(tmp_path / "thumb.jpg")

        ffmpeg_service.normalize_and_concat(assets["clips"], job.aspect_ratio, concat_path)
        ffmpeg_service.attach_narration(
            concat_path, assets["narration"], job.duration_seconds, narrated_path
        )
        ffmpeg_service.hard_cap_duration(narrated_path, job.duration_seconds, final_path)
        ffmpeg_service.generate_thumbnail(final_path, thumb_path)

        video_key = f"videos/{job.id}.mp4"
        thumb_key = f"videos/{job.id}_thumb.jpg"
        _upload(video_key, Path(final_path).read_bytes(), "video/mp4")
        _upload(thumb_key, Path(thumb_path).read_bytes(), "image/jpeg")

    video_job_service.mark_status(db, job.id, "ready", video_url=video_key, thumbnail_url=thumb_key)
