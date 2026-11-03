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
