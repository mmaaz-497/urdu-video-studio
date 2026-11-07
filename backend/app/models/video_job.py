import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

VIDEO_JOB_STATUSES = (
    "queued",
    "preparing",
    "generating_scenes",
    "adding_voice",
    "finalizing",
    "ready",
    "failed",
)


class VideoJob(Base):
    __tablename__ = "video_jobs"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "idempotency_key", name="uq_video_jobs_student_idempotency_key"
        ),
        CheckConstraint("duration_seconds IN (5, 10, 15)", name="ck_video_jobs_duration_seconds"),
        CheckConstraint("aspect_ratio IN ('16:9', '9:16')", name="ck_video_jobs_aspect_ratio"),
        CheckConstraint("voice_id IN ('male', 'female')", name="ck_video_jobs_voice_id"),
        CheckConstraint(
            "status IN ('queued','preparing','generating_scenes','adding_voice',"
            "'finalizing','ready','failed')",
            name="ck_video_jobs_status",
        ),
        Index("ix_video_jobs_student_created_at", "student_id", "created_at"),
        Index("ix_video_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    raw_idea: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_idea: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    urdu_script: Mapped[str] = mapped_column(Text, nullable=False)
    scenes: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String, nullable=False)
    voice_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="queued")
    progress_current_scene: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    progress_total_scenes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    counted_toward_limit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student = relationship("Student", back_populates="video_jobs")
