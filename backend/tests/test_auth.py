import redis as redis_sync

from app.core.config import get_settings


def test_register_creates_session_and_profile(client):
    resp = client.post(
        "/auth/register", json={"email": "new@example.com", "password": "password123"}
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["usage"]["videoLimit"] >= 1
    assert "session_id" in resp.cookies
    assert "csrf_token" in resp.cookies


def test_register_rejects_duplicate_email(client, student_factory):
    student_factory(email="dup@example.com")

    resp = client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "password123"}
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_rejects_short_password(client):
    resp = client.post("/auth/register", json={"email": "weak@example.com", "password": "short"})

    assert resp.status_code == 422


def test_login_success(client, student_factory):
    student_factory(email="login@example.com", password="correct-password")

    resp = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "correct-password"}
    )

    assert resp.status_code == 200
    assert "session_id" in resp.cookies


def test_login_bad_credentials(client, student_factory):
    student_factory(email="baduser@example.com", password="correct-password")

    resp = client.post(
        "/auth/login", json={"email": "baduser@example.com", "password": "wrong-password"}
    )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_email_is_generic(client):
    resp = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_requires_session(client):
    resp = client.get("/me")

    assert resp.status_code == 401


def test_me_returns_profile_when_logged_in(client, student_factory):
    student_factory(email="me@example.com", password="password123")
    client.post("/auth/login", json={"email": "me@example.com", "password": "password123"})

    resp = client.get("/me")

    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_logout_requires_csrf_header(client, student_factory):
    student_factory(email="logout@example.com", password="password123")
    client.post("/auth/login", json={"email": "logout@example.com", "password": "password123"})

    resp_no_csrf = client.post("/auth/logout")
    assert resp_no_csrf.status_code == 403

    csrf_token = client.cookies.get("csrf_token")
    resp = client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 204

    resp_me = client.get("/me")
    assert resp_me.status_code == 401


def test_session_expiry_rejected(client, student_factory):
    student_factory(email="expiry@example.com", password="password123")
    client.post("/auth/login", json={"email": "expiry@example.com", "password": "password123"})

    # Simulate TTL expiry out-of-band via a plain sync Redis client, so this
    # doesn't touch the app's event-loop-bound asyncio Redis client.
    session_id = client.cookies.get("session_id")
    sync_redis = redis_sync.Redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    sync_redis.delete(f"session:{session_id}")

    resp = client.get("/me")
    assert resp.status_code == 401


# --- Password reset (US3, FR-003 / FR-004) ---------------------------------

from datetime import UTC, datetime, timedelta  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.models.password_reset_token import PasswordResetToken  # noqa: E402


class _CapturingSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        self.sent.append((to_email, reset_link))


@pytest.fixture
def mail(monkeypatch):
    sender = _CapturingSender()
    monkeypatch.setattr("app.api.auth.get_email_sender", lambda: sender)
    return sender


def _token_from(sender: _CapturingSender, index: int = -1) -> str:
    link = sender.sent[index][1]
    return parse_qs(urlparse(link).query)["token"][0]


def _request_reset(client, email: str):
    return client.post("/auth/forgot-password", json={"email": email})


def test_forgot_password_unknown_email_is_202_and_sends_nothing(client, mail):
    resp = _request_reset(client, "ghost@example.com")

    assert resp.status_code == 202
    assert mail.sent == []


def test_forgot_password_response_identical_for_known_email(client, student_factory, mail):
    student_factory(email="known@example.com")

    known = _request_reset(client, "known@example.com")
    unknown = _request_reset(client, "ghost@example.com")

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(mail.sent) == 1


def test_reset_issue_and_consume(client, student_factory, db_session, mail):
    student_factory(email="reset@example.com", password="old-password")
    _request_reset(client, "reset@example.com")
    token = _token_from(mail)

    # Only the hash is stored, never the raw token.
    row = db_session.execute(select(PasswordResetToken)).scalar_one()
    assert row.token_hash != token
    assert len(row.token_hash) == 64

    resp = client.post("/auth/reset-password", json={"token": token, "newPassword": "new-password"})
    assert resp.status_code == 200

    old = client.post(
        "/auth/login", json={"email": "reset@example.com", "password": "old-password"}
    )
    new = client.post(
        "/auth/login", json={"email": "reset@example.com", "password": "new-password"}
    )
    assert old.status_code == 401
    assert new.status_code == 200


def test_reset_rejects_expired_token(client, student_factory, db_session, mail):
    student_factory(email="expired@example.com", password="old-password")
    _request_reset(client, "expired@example.com")
    token = _token_from(mail)
    row = db_session.execute(select(PasswordResetToken)).scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    resp = client.post("/auth/reset-password", json={"token": token, "newPassword": "new-password"})

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"
    ok = client.post(
        "/auth/login", json={"email": "expired@example.com", "password": "old-password"}
    )
    assert ok.status_code == 200


def test_reset_token_is_single_use(client, student_factory, mail):
    student_factory(email="once@example.com")
    _request_reset(client, "once@example.com")
    token = _token_from(mail)

    first = client.post(
        "/auth/reset-password", json={"token": token, "newPassword": "first-password"}
    )
    second = client.post(
        "/auth/reset-password", json={"token": token, "newPassword": "second-password"}
    )

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "INVALID_RESET_TOKEN"
    login = client.post(
        "/auth/login", json={"email": "once@example.com", "password": "first-password"}
    )
    assert login.status_code == 200


def test_reset_older_token_superseded_by_newer(client, student_factory, mail):
    student_factory(email="twice@example.com")
    _request_reset(client, "twice@example.com")
    _request_reset(client, "twice@example.com")
    old_token, new_token = _token_from(mail, 0), _token_from(mail, 1)

    stale = client.post(
        "/auth/reset-password", json={"token": old_token, "newPassword": "stale-password"}
    )
    fresh = client.post(
        "/auth/reset-password", json={"token": new_token, "newPassword": "fresh-password"}
    )

    assert stale.status_code == 400
    assert stale.json()["error"]["code"] == "INVALID_RESET_TOKEN"
    assert fresh.status_code == 200


def test_reset_rejects_unknown_token_and_short_password(client, student_factory, mail):
    student_factory(email="short@example.com")
    _request_reset(client, "short@example.com")
    token = _token_from(mail)

    unknown = client.post(
        "/auth/reset-password", json={"token": "nope", "newPassword": "new-password"}
    )
    short = client.post("/auth/reset-password", json={"token": token, "newPassword": "short"})

    assert unknown.status_code == 400
    assert short.status_code == 422


def test_reset_revokes_all_existing_sessions(client, student_factory, mail):
    student_factory(email="revoke@example.com", password="old-password")
    creds = {"email": "revoke@example.com", "password": "old-password"}

    # Two independent sessions for the same student (e.g. owner + attacker).
    client.post("/auth/login", json=creds)
    first_session = client.cookies.get("session_id")
    client.post("/auth/login", json=creds)
    second_session = client.cookies.get("session_id")
    assert first_session != second_session

    def me_with(session_id: str) -> int:
        client.cookies.clear()
        client.cookies.set("session_id", session_id)
        return client.get("/me").status_code

    assert me_with(first_session) == 200
    assert me_with(second_session) == 200

    _request_reset(client, "revoke@example.com")
    resp = client.post(
        "/auth/reset-password",
        json={"token": _token_from(mail), "newPassword": "new-password"},
    )
    assert resp.status_code == 200

    assert me_with(first_session) == 401
    assert me_with(second_session) == 401
