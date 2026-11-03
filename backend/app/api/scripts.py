import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.csrf import require_csrf
from app.core.db import get_db
from app.core.errors import AppError
from app.core.redis_client import call_with_timeout, get_redis
from app.core.sessions import require_session
from app.schemas.scripts import GeneratedScript, GenerateScriptRequest
from app.services import llm_service, usage_service

router = APIRouter()

# Covers moderation (10s) + up to two LLM calls (20s each) with margin, so a
# legitimate in-flight request never looks "stuck" to a concurrent duplicate.
_PENDING_TTL_SECONDS = 55
_CACHE_TTL_SECONDS = 60


def _idem_key(student_id: uuid.UUID, idempotency_key: uuid.UUID) -> str:
    return f"script-idem:{student_id}:{idempotency_key}"


@router.post(
    "/scripts",
    status_code=201,
    response_model=GeneratedScript,
    dependencies=[Depends(require_csrf)],
)
async def create_script(
    payload: GenerateScriptRequest,
    db: Session = Depends(get_db),
    student_id: uuid.UUID = Depends(require_session),
) -> GeneratedScript:
    redis = get_redis()
    key = _idem_key(student_id, payload.idempotencyKey)

    claimed = await call_with_timeout(redis.set(key, "pending", nx=True, ex=_PENDING_TTL_SECONDS))
    if not claimed:
        cached = await call_with_timeout(redis.get(key))
        if cached is None or cached == "pending":
            raise AppError(
                "REQUEST_IN_PROGRESS", "This request is already being processed. Please wait."
            )
        return GeneratedScript.model_validate_json(cached)

    try:
        incremented = usage_service.try_increment_script_count(db, student_id)
        db.commit()
        if not incremented:
            raise AppError(
                "DAILY_SCRIPT_LIMIT_REACHED",
                "You've used all your script generations for today. Come back after "
                "midnight (Asia/Karachi) for more.",
                extra={"resetsAt": usage_service.resets_at().isoformat()},
            )

        output = await llm_service.generate_script(payload.idea, payload.durationSeconds)
        response = GeneratedScript(
            correctedIdea=output.corrected_idea,
            title=output.title,
            urduScript=output.urdu_script,
            scenes=output.scenes,
            wordCount=llm_service.word_count(output.urdu_script),
            wordLimit=llm_service.word_limit_for(payload.durationSeconds),
        )
        await call_with_timeout(redis.set(key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS))
        return response
    except Exception:
        await call_with_timeout(redis.delete(key))
        raise
