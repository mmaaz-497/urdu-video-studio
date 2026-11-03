import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.csrf import issue_csrf_cookie, require_csrf
from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.core.sessions import (
    clear_session_cookie,
    create_session,
    destroy_session,
    require_session,
    set_session_cookie,
)
from app.models.student import Student
from app.schemas.auth import LoginRequest, RegisterRequest, StudentProfile
from app.services import usage_service

router = APIRouter()


def _build_profile(db: Session, student: Student) -> StudentProfile:
    usage = usage_service.get_usage_summary(db, student.id)
    return StudentProfile(
        id=student.id, email=student.email, createdAt=student.created_at, usage=usage
    )


@router.post("/auth/register", status_code=201, response_model=StudentProfile)
async def register(
    payload: RegisterRequest, response: Response, db: Session = Depends(get_db)
) -> StudentProfile:
    existing = db.execute(
        select(Student).where(Student.email == payload.email)
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("EMAIL_ALREADY_REGISTERED", "An account with this email already exists.")

    student = Student(email=payload.email, password_hash=hash_password(payload.password))
    db.add(student)
    db.commit()

    session_id = await create_session(student.id)
    set_session_cookie(response, session_id)
    issue_csrf_cookie(response)
    return _build_profile(db, student)


@router.post("/auth/login", response_model=StudentProfile)
async def login(
    payload: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> StudentProfile:
    student = db.execute(select(Student).where(Student.email == payload.email)).scalar_one_or_none()
    if student is None or not verify_password(student.password_hash, payload.password):
        raise AppError("INVALID_CREDENTIALS", "Invalid email or password.")

    student.last_login_at = datetime.now(UTC)
    db.commit()

    session_id = await create_session(student.id)
    set_session_cookie(response, session_id)
    issue_csrf_cookie(response)
    return _build_profile(db, student)


@router.post("/auth/logout", status_code=204, dependencies=[Depends(require_csrf)])
async def logout(
    request: Request, response: Response, _student_id: uuid.UUID = Depends(require_session)
) -> Response:
    await destroy_session(request.state.session_id)
    clear_session_cookie(response)
    return Response(status_code=204)


@router.get("/me", response_model=StudentProfile)
async def me(
    db: Session = Depends(get_db), student_id: uuid.UUID = Depends(require_session)
) -> StudentProfile:
    student = db.get(Student, student_id)
    if student is None:
        raise AppError("UNAUTHENTICATED", "Please log in again.")
    return _build_profile(db, student)
