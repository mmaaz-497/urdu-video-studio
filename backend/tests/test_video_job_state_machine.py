import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.models.video_job import VideoJob
from app.services import video_pipeline
from app.services.mock_provider import pick_assets
from app.services.video_pipeline import run_job

SHORT_SCRIPT = " ".join(["لفظ"] * 10)  # 10 words -> fits a 5s (1-scene, limit-12) video


def _video_body(**overrides) -> dict:
    body = {
        "idempotencyKey": str(uuid.uuid4()),
        "correctedIdea": "Ek acha idea",
        "title": "Test Video",
        "urduScript": SHORT_SCRIPT,
        "scenes": ["A student writing notes in a classroom"],
        "durationSeconds": 5,
        "aspectRatio": "16:9",
        "voiceId": "male",
    }
    body.update(overrides)
    return body


def test_happy_path_queued_to_ready(auth_client, db_session):
    client, headers, _student = auth_client

    resp = client.post("/videos", json=_video_body(), headers=headers)
    assert resp.status_code == 201
    job_id = resp.json()["id"]
    assert resp.json()["status"] == "queued"

    run_job(job_id)
    db_session.expire_all()

    poll = client.get(f"/videos/{job_id}", headers=headers)
    assert poll.status_code == 200
    final = poll.json()
    assert final["status"] == "ready"
    assert final["videoUrl"] is not None
    assert final["thumbnailUrl"] is not None
    assert final["progressCurrentScene"] == final["progressTotalScenes"] == 1


def test_idempotent_replay_on_duplicate_idempotency_key(auth_client):
    client, headers, _student = auth_client
    body = _video_body()

    first = client.post("/videos", json=body, headers=headers)
    second = client.post("/videos", json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    usage = client.get("/me").json()["usage"]["videosUsedToday"]
    assert usage == 1  # not double-counted


def test_daily_video_limit_reached(auth_client):
    client, headers, _student = auth_client
    limit = get_settings().DAILY_VIDEO_LIMIT

    for _ in range(limit):
        resp = client.post("/videos", json=_video_body(), headers=headers)
        assert resp.status_code == 201

    over_limit = client.post("/videos", json=_video_body(), headers=headers)
    assert over_limit.status_code == 429
    assert over_limit.json()["error"]["code"] == "DAILY_VIDEO_LIMIT_REACHED"
    assert "resetsAt" in over_limit.json()["error"]


def test_failed_job_is_not_counted_toward_limit(auth_client, db_session, monkeypatch):
    client, headers, _student = auth_client

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated asset failure")

    monkeypatch.setattr(video_pipeline.mock_provider, "pick_assets", _boom)

    resp = client.post("/videos", json=_video_body(), headers=headers)
    job_id = resp.json()["id"]

    run_job(job_id)
    db_session.expire_all()

    failed = client.get(f"/videos/{job_id}", headers=headers).json()
    assert failed["status"] == "failed"
    assert failed["failureReason"]

    usage = client.get("/me").json()["usage"]["videosUsedToday"]
    assert usage == 0  # the failed job's claim was reversed


def test_retry_after_failure_creates_a_new_job(auth_client, db_session, monkeypatch):
    """Simulates what the (Phase 4) retry endpoint will do: re-submit the same
    approved script under a brand-new idempotencyKey rather than mutating the
    terminal failed job (data-model.md State Transitions)."""
    client, headers, student = auth_client

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated asset failure")

    monkeypatch.setattr(video_pipeline.mock_provider, "pick_assets", _boom)

    first_resp = client.post("/videos", json=_video_body(), headers=headers)
    first_id = first_resp.json()["id"]
    run_job(first_id)
    db_session.expire_all()
    assert client.get(f"/videos/{first_id}", headers=headers).json()["status"] == "failed"

    monkeypatch.undo()  # restore pick_assets so the retry can actually succeed

    retry_resp = client.post("/videos", json=_video_body(), headers=headers)
    assert retry_resp.status_code == 201
    retry_id = retry_resp.json()["id"]
    assert retry_id != first_id

    usage = client.get("/me").json()["usage"]["videosUsedToday"]
    assert usage == 1  # failed job not counted, new job counted once


def test_stale_job_sweeper_marks_timed_out_jobs_failed(auth_client, db_session):
    from app.scheduler import STALE_FAILURE_REASON, sweep_once

    client, headers, student = auth_client

    resp = client.post("/videos", json=_video_body(), headers=headers)
    job_id = resp.json()["id"]

    job = db_session.get(VideoJob, uuid.UUID(job_id))
    max_processing = get_settings().MAX_PROCESSING_SECONDS
    job.created_at = datetime.now(UTC) - timedelta(seconds=max_processing + 30)
    db_session.commit()

    swept = sweep_once()
    db_session.expire_all()

    assert swept == 1
    failed = client.get(f"/videos/{job_id}", headers=headers).json()
    assert failed["status"] == "failed"
    assert failed["failureReason"] == STALE_FAILURE_REASON

    usage = client.get("/me").json()["usage"]["videosUsedToday"]
    assert usage == 0


def test_mock_provider_pick_assets_returns_matching_counts():
    assets = pick_assets("16:9", 2, "male")
    assert len(assets["clips"]) == 2
    assert assets["narration"].endswith("male_2.mp3")
