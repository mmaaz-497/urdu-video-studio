import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

VideoJobStatus = Literal[
    "queued", "preparing", "generating_scenes", "adding_voice", "finalizing", "ready", "failed"
]


class CreateVideoJobRequest(BaseModel):
    idempotencyKey: uuid.UUID
    correctedIdea: str
    title: str
    urduScript: str
    scenes: list[str] = Field(min_length=1, max_length=3)
    durationSeconds: Literal[5, 10, 15]
    aspectRatio: Literal["16:9", "9:16"]
    voiceId: Literal["male", "female"]


class VideoJobSummary(BaseModel):
    id: uuid.UUID
    title: str
    thumbnailUrl: str | None = None
    status: VideoJobStatus
    durationSeconds: int
    aspectRatio: str
    createdAt: datetime


class VideoJob(VideoJobSummary):
    progressCurrentScene: int | None = None
    progressTotalScenes: int
    failureReason: str | None = None
    videoUrl: str | None = None
    urduScript: str
    correctedIdea: str
    voiceId: Literal["male", "female"]
    completedAt: datetime | None = None


class VideoJobListItem(VideoJobSummary):
    failureReason: str | None = None
    videoUrl: str | None = None


class VideoJobListResponse(BaseModel):
    items: list[VideoJobListItem]
    nextCursor: str | None = None
