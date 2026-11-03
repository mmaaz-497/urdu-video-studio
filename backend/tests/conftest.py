import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, engine, get_db
from app.core.security import hash_password
from app.main import app
from app.models.student import Student

TABLES_TO_RESET = ("video_jobs", "password_reset_tokens", "usage_counters", "students")


@pytest.fixture(autouse=True)
def _reset_tables_after_test() -> Generator[None, None, None]:
    """Each test starts from a clean slate; rolled back by truncating afterward
    rather than wrapping in a savepoint, since application code commits."""
    yield
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {', '.join(TABLES_TO_RESET)} CASCADE"))


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()

    def _override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    # Session/CSRF cookies are Secure; httpx's cookie jar only persists and
    # resends Secure cookies over an https:// base_url.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


@pytest.fixture
def student_factory(db_session: Session):
    def _create(email: str | None = None, password: str = "password123") -> Student:
        student = Student(
            email=email or f"{uuid.uuid4().hex}@example.com",
            password_hash=hash_password(password),
        )
        db_session.add(student)
        db_session.commit()
        return student

    return _create


@pytest.fixture
def auth_client(client: TestClient, student_factory):
    """A logged-in TestClient plus the X-CSRF-Token header required for any
    state-changing request, and the logged-in Student row."""
    student = student_factory(password="password123")
    resp = client.post("/auth/login", json={"email": student.email, "password": "password123"})
    assert resp.status_code == 200
    csrf_token = client.cookies.get("csrf_token")
    return client, {"X-CSRF-Token": csrf_token}, student
