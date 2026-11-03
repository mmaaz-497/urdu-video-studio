import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    video_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    script_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    student = relationship("Student", back_populates="usage_counters")
