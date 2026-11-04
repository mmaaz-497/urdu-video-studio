import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.csrf import require_csrf
from app.core.db import get_db
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.sessions import require_session
from app.models.video_job import VideoJob as VideoJobModel
from app.schemas.videos import CreateVideoJobRequest, VideoJobListItem, VideoJobListResponse
from app.schemas.videos import VideoJob as VideoJobSchema
from app.services import video_job_service
from app.services.storage_service import get_storage
from app.services.video_pipeline import run_job
from app.worker import get_queue

router = APIRouter()
logger = get_logger(__name__)


async def _get_owned_job(db: Session, id: uuid.UUID, student_id: uuid.UUID) -> VideoJobModel:
    job = video_job_service.get_job(db, id)
    if job is None or job.student_id != student_id:
        raise AppError("NOT_FOUND", "Video not found.")
    return job


async def _to_list_item(job: VideoJobModel) -> VideoJobListItem:
    storage = get_storage()
    video_url = await storage.get_download_url(job.video_url) if job.video_url else None
    thumbnail_url = (
        await storage.get_download_url(job.thumbnail_url) if job.thumbnail_url else None
    )
    return VideoJobListItem(
        id=job.id,
        title=job.title,
        thumbnailUrl=thumbnail_url,
        status=job.status,
        durationSeconds=job.duration_seconds,
        aspectRatio=job.aspect_ratio,
        createdAt=job.created_at,
        failureReason=job.failure_reason,
        videoUrl=video_url,
    )


async def _to_schema(job: VideoJobModel) -> VideoJobSchema:
    storage = get_storage()
    video_url = await storage.get_download_url(job.video_url) if job.video_url else None
    thumbnail_url = (
        await storage.get_download_url(job.thumbnail_url) if job.thumbnail_url else None
    )
    return VideoJobSchema(
        id=job.id,
        title=job.title,
        thumbnailUrl=thumbnail_url,
        status=job.status,
        durationSeconds=job.duration_seconds,
        aspectRatio=job.aspect_ratio,
        createdAt=job.created_at,
        progressCurrentScene=job.progress_current_scene,
        progressTotalScenes=job.progress_total_scenes,
        failureReason=job.failure_reason,
        videoUrl=video_url,
        urduScript=job.urdu_script,
        correctedIdea=job.corrected_idea,
        voiceId=job.voice_id,
        completedAt=job.completed_at,
    )


@router.post(
    "/videos",
    status_code=201,
    response_model=VideoJobSchema,
    dependencies=[Depends(require_csrf)],
)
async def create_video(
    payload: CreateVideoJobRequest,
    db: Session = Depends(get_db),
    student_id: uuid.UUID = Depends(require_session),
) -> VideoJobSchema:
    job, created = video_job_service.create_job(db, student_id, payload)
    if created:
        settings = get_settings()
        get_queue().enqueue(run_job, str(job.id), job_timeout=settings.MAX_PROCESSING_SECONDS + 60)
    return await _to_schema(job)


@router.get("/videos", response_model=VideoJobListResponse)
async def list_videos(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    student_id: uuid.UUID = Depends(require_session),
) -> VideoJobListResponse:
    jobs, next_cursor = video_job_service.list_for_student(db, student_id, cursor, limit)
    items = [await _to_list_item(job) for job in jobs]
    return VideoJobListResponse(items=items, nextCursor=next_cursor)


@router.get("/videos/{id}", response_model=VideoJobSchema)
async def get_video(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    student_id: uuid.UUID = Depends(require_session),
) -> VideoJobSchema:
    job = await _get_owned_job(db, id, student_id)
    return await _to_schema(job)


@router.delete("/videos/{id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_video(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    student_id: uuid.UUID = Depends(require_session),
) -> None:
    job = await _get_owned_job(db, id, student_id)
    video_key, thumbnail_key = job.video_url, job.thumbnail_url
    video_job_service.delete(db, job)

    storage = get_storage()
    for key in (video_key, thumbnail_key):
        if not key:
            continue
        try:
            await storage.delete(key)
        except Exception:
            logger.warning("video_delete_storage_cleanup_failed", extra={"key": key})


@router.post(
    "/videos/{id}/retry",
    status_code=201,
    response_model=VideoJobSchema,
    dependencies=[Depends(require_csrf)],
)
async def retry_video(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    student_id: uuid.UUID = Depends(require_session),
) -> VideoJobSchema:
    job = await _get_owned_job(db, id, student_id)
    new_job, _created = video_job_service.retry(db, job)
    settings = get_settings()
    get_queue().enqueue(run_job, str(new_job.id), job_timeout=settings.MAX_PROCESSING_SECONDS + 60)
    return await _to_schema(new_job)
