"""Test session setup.

SAFETY GUARD — runs before anything from `app` is imported (the engine is built at import
time). These tests TRUNCATE tables, so they must never see the dev/production database:

* the database comes ONLY from TEST_DATABASE_URL (process env, or backend/.env); the regular
  DATABASE_URL is never used as a fallback, and is overwritten for this process;
* TEST_DATABASE_URL must be set and its database name must end in "_test", otherwise the run
  aborts immediately;
* VIDEO_PROVIDER is forced to "mock" and STORAGE_PROVIDER to "local" (in a temp dir), so a test
  can never spend GPU time or touch R2.
"""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def _abort(message: str) -> None:
    pytest.exit(f"\n\nREFUSING TO RUN TESTS: {message}\n", returncode=2)


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(
        Path(__file__).resolve().parents[1] / ".env"
    ).get("TEST_DATABASE_URL")
    if not url:
        _abort(
            "TEST_DATABASE_URL is not set. Create a separate database whose name ends in "
            '"_test" and set TEST_DATABASE_URL to it (see backend/.env.example). '
            "DATABASE_URL is deliberately never used for tests: they truncate tables."
        )
    try:
        name = make_url(url).database or ""
    except Exception:  # noqa: BLE001
        _abort("TEST_DATABASE_URL is not a valid database URL.")
    if not name.endswith("_test"):
        _abort(
            f'the database name in TEST_DATABASE_URL is "{name}"; it must end in "_test" '
            "so the dev/production database can never be truncated."
        )
    return url


os.environ["DATABASE_URL"] = _test_database_url()
os.environ["VIDEO_PROVIDER"] = "mock"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = tempfile.mkdtemp(prefix="uvs-test-storage-")

import uuid  # noqa: E402  (must follow the safety guard above)
from collections.abc import Generator  # noqa: E402  (must follow the safety guard above)

from fastapi.testclient import TestClient  # noqa: E402  (must follow the safety guard above)
from sqlalchemy import text  # noqa: E402  (must follow the safety guard above)
from sqlalchemy.orm import Session  # noqa: E402  (must follow the safety guard above)

from app.core.db import (  # noqa: E402
    SessionLocal,
    engine,
    get_db,
)  # noqa: E402  (must follow the safety guard above)
from app.core.security import hash_password  # noqa: E402  (must follow the safety guard above)
from app.main import app  # noqa: E402  (must follow the safety guard above)
from app.models.student import Student  # noqa: E402  (must follow the safety guard above)

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
