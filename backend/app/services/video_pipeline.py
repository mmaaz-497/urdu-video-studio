import asyncio
import tempfile
import time
import uuid
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.core.logging import get_logger
from app.services import (
    ffmpeg_service,
    mock_provider,
    runpod_provider,
    usage_service,
    video_job_service,
)
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
            if get_settings().VIDEO_PROVIDER == "runpod":
                _run_runpod(db, job)
            else:
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

    with tempfile.TemporaryDirectory(prefix=f"job-{job.id}-") as tmp:
        _finalize(db, job, assets["clips"], assets["narration"], Path(tmp))


def _finalize(
    db,
    job,
    clips: list[str],
    narration: str,
    tmp_path: Path,
    intermediate_keys: list[str] | None = None,
) -> None:
    """FFmpeg assemble + upload + mark ready, then best-effort delete of the job's raw
    intermediate storage keys. Shared by the mock and runpod paths (the mock path
    writes no intermediates to storage, so it passes none)."""
    video_job_service.mark_status(db, job.id, "finalizing")
    concat_path = str(tmp_path / "concat.mp4")
    narrated_path = str(tmp_path / "narrated.mp4")
    final_path = str(tmp_path / "final.mp4")
    thumb_path = str(tmp_path / "thumb.jpg")

    ffmpeg_service.normalize_and_concat(clips, job.aspect_ratio, concat_path)
    ffmpeg_service.attach_narration(concat_path, narration, job.duration_seconds, narrated_path)
    ffmpeg_service.hard_cap_duration(narrated_path, job.duration_seconds, final_path)
    ffmpeg_service.generate_thumbnail(final_path, thumb_path)

    video_key = f"videos/{job.id}.mp4"
    thumb_key = f"videos/{job.id}_thumb.jpg"
    _upload(video_key, Path(final_path).read_bytes(), "video/mp4")
    _upload(thumb_key, Path(thumb_path).read_bytes(), "image/jpeg")

    video_job_service.mark_status(db, job.id, "ready", video_url=video_key, thumbnail_url=thumb_key)
    _cleanup_intermediates(intermediate_keys or [])


def _cleanup_intermediates(keys: list[str]) -> None:
    """Best-effort: a failed delete is logged and never fails the job."""
    if not keys:
        return
    storage = get_storage()
    for key in keys:
        try:
            asyncio.run(storage.delete(key))
        except Exception:  # noqa: BLE001
            logger.warning("intermediate_cleanup_failed", extra={"key": key}, exc_info=True)


def _download(url: str, dest: Path) -> str:
    try:
        with httpx.stream("GET", url, timeout=30, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
    except httpx.HTTPError as exc:
        logger.error("gpu_asset_download_failed", extra={"error": str(exc)})
        raise AppError(
            "STORAGE_UNAVAILABLE", "Storage is temporarily unavailable. Please try again."
        ) from exc
    return str(dest)


def _run_runpod(db, job) -> None:
    settings = get_settings()
    if settings.STORAGE_PROVIDER != "r2":
        # Workers PUT to presigned URLs; the local-disk backend has none.
        raise AppError(
            "RUNPOD_UNAVAILABLE", "Video generation is not configured. Please try later."
        )

    scene_count = job.progress_total_scenes
    storage = get_storage()
    video_job_service.mark_status(db, job.id, "preparing")

    clip_keys = [f"jobs/{job.id}/scene{i}.mp4" for i in range(1, scene_count + 1)]
    narration_key = f"jobs/{job.id}/narration.wav"
    put_urls = {
        "clips": [asyncio.run(storage.get_presigned_put_url(k, "video/mp4")) for k in clip_keys],
        "narration": asyncio.run(storage.get_presigned_put_url(narration_key, "audio/wav")),
    }

    video_job_service.mark_status(db, job.id, "generating_scenes", progress_current_scene=0)

    def _on_progress(done: int) -> None:
        video_job_service.mark_status(
            db, job.id, "generating_scenes", progress_current_scene=min(done, scene_count)
        )

    result = runpod_provider.generate(
        scenes=list(job.scenes),
        aspect_ratio=job.aspect_ratio,
        narration=job.urdu_script,
        voice_id=job.voice_id,
        presigned_put_urls=put_urls,
        on_progress=_on_progress,
    )
    narration_seconds = float(result.get("narration_duration_seconds") or 0)
    logger.info(
        "runpod_job_generated",
        extra={
            "job_id": str(job.id),
            "narration_seconds": narration_seconds,
            "target_seconds": job.duration_seconds,
        },
    )
    if narration_seconds > job.duration_seconds * ffmpeg_service.MAX_NARRATION_SPEEDUP:
        # Measured by the worker: it can't fit even with the allowed atempo speed-up.
        raise AppError(
            "SCRIPT_TOO_LONG", "Script is too long for the chosen duration — please shorten it"
        )

    video_job_service.mark_status(db, job.id, "adding_voice", progress_current_scene=scene_count)
    with tempfile.TemporaryDirectory(prefix=f"job-{job.id}-") as tmp:
        tmp_path = Path(tmp)
        clips = [
            _download(asyncio.run(storage.get_download_url(k)), tmp_path / f"scene{i}.mp4")
            for i, k in enumerate(clip_keys, start=1)
        ]
        narration = _download(
            asyncio.run(storage.get_download_url(narration_key)), tmp_path / "narration.wav"
        )
        _finalize(db, job, clips, narration, tmp_path, [*clip_keys, narration_key])
