import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.core.sessions import destroy_all_sessions
from app.models.password_reset_token import PasswordResetToken
from app.models.student import Student

TOKEN_TTL = timedelta(minutes=30)
_INVALID_MESSAGE = "This reset link is invalid, expired, or has already been used."


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_token(db: Session, student: Student) -> str:
    """Invalidate any outstanding token, then issue a new one. Returns the raw
    token (never stored; only its SHA-256 hash is persisted)."""
    now = datetime.now(UTC)
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.student_id == student.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.invalidated_at.is_(None),
        )
        .values(invalidated_at=now)
    )
    raw = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(student_id=student.id, token_hash=_hash(raw), expires_at=now + TOKEN_TTL)
    )
    db.commit()
    return raw


def _load_valid(db: Session, raw_token: str, *, lock: bool = False) -> PasswordResetToken:
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash(raw_token))
    if lock:
        stmt = stmt.with_for_update()
    token = db.execute(stmt).scalar_one_or_none()
    if (
        token is None
        or token.used_at is not None
        or token.invalidated_at is not None
        or token.expires_at <= datetime.now(UTC)
    ):
        raise AppError("INVALID_RESET_TOKEN", _INVALID_MESSAGE)
    return token


def verify_token(db: Session, raw_token: str) -> PasswordResetToken:
    return _load_valid(db, raw_token)


async def consume_token(db: Session, raw_token: str, new_password: str) -> None:
    token = _load_valid(db, raw_token, lock=True)
    student = db.get(Student, token.student_id)
    if student is None:
        raise AppError("INVALID_RESET_TOKEN", _INVALID_MESSAGE)
    # Revoke before committing: if the session store is down this raises and the
    # token stays unused (safe to retry), rather than changing the password while
    # a possibly attacker-held session survives.
    await destroy_all_sessions(student.id)
    student.password_hash = hash_password(new_password)
    token.used_at = datetime.now(UTC)
    db.commit()
