import uuid
from typing import Literal

from pydantic import BaseModel, Field


class GenerateScriptRequest(BaseModel):
    idempotencyKey: uuid.UUID
    idea: str = Field(min_length=10, max_length=500)
    durationSeconds: Literal[5, 10, 15]
    aspectRatio: Literal["16:9", "9:16"]
    voiceId: Literal["male", "female"]


class Scene(BaseModel):
    """One 5 s segment: the English prompt for Wan and the Urdu narration for the same moment."""

    visualPrompt: str
    narrationUr: str


class GeneratedScript(BaseModel):
    correctedIdea: str
    title: str
    urduScript: str  # narrations joined in order; display / backward compatibility only
    scenes: list[Scene] = Field(min_length=1, max_length=3)
    wordCount: int  # words across all narrations
    wordLimit: int  # whole-script ceiling for the chosen duration
    sceneWordLimit: int  # hard per-scene ceiling (enforced on POST /videos)
