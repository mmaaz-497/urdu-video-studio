import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UsageSummary(BaseModel):
    videosUsedToday: int
    videoLimit: int
    scriptsUsedToday: int
    scriptLimit: int
    resetsAt: datetime


class StudentProfile(BaseModel):
    id: uuid.UUID
    email: str
    createdAt: datetime
    usage: UsageSummary
