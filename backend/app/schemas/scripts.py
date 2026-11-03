import uuid
from typing import Literal

from pydantic import BaseModel, Field


class GenerateScriptRequest(BaseModel):
    idempotencyKey: uuid.UUID
    idea: str = Field(min_length=10, max_length=500)
    durationSeconds: Literal[5, 10, 15]
    aspectRatio: Literal["16:9", "9:16"]
    voiceId: Literal["male", "female"]


class GeneratedScript(BaseModel):
    correctedIdea: str
    title: str
    urduScript: str
    scenes: list[str] = Field(min_length=1, max_length=3)
    wordCount: int
    wordLimit: int
