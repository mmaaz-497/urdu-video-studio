from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.sessions import require_session

router = APIRouter()


class Voice(BaseModel):
    id: str
    label: str
    previewUrl: str


_VOICES = [
    Voice(id="male", label="Male voice", previewUrl="/assets/voices/male_preview.mp3"),
    Voice(id="female", label="Female voice", previewUrl="/assets/voices/female_preview.mp3"),
]


@router.get("/voices", response_model=list[Voice])
async def list_voices(_student_id=Depends(require_session)) -> list[Voice]:
    return _VOICES
