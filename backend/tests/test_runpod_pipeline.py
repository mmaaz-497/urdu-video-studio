import shutil
import uuid

import pytest

from app.core.config import get_settings
from app.core.errors import AppError
from app.services import runpod_provider, video_pipeline
from app.services.mock_provider import pick_assets
from app.services.video_pipeline import run_job

SCRIPT = " ".join(["لفظ"] * 10)


def _body() -> dict:
    return {
        "idempotencyKey": str(uuid.uuid4()),
        "correctedIdea": "idea",
        "title": "Test Video",
        "urduScript": SCRIPT,
        "scenes": ["A student writing notes in a classroom"],
        "durationSeconds": 5,
        "aspectRatio": "16:9",
        "voiceId": "male",
    }


class FakeStorage:
    def __init__(self):
        self.uploaded: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def get_presigned_put_url(self, key, content_type):
        return f"https://r2.test/put/{key}?ct={content_type}"

    async def get_download_url(self, key):
        return f"https://r2.test/get/{key}"

    async def upload(self, key, data, content_type):
        self.uploaded[key] = data

    async def delete(self, key):
        self.deleted.append(key)


@pytest.fixture
def runpod_env(monkeypatch):
    settings = get_settings().model_copy(
        update={"VIDEO_PROVIDER": "runpod", "STORAGE_PROVIDER": "r2"}
    )
    storage = FakeStorage()
    assets = pick_assets("16:9", 1, "male")

    monkeypatch.setattr(video_pipeline, "get_settings", lambda: settings)
    monkeypatch.setattr(video_pipeline, "get_storage", lambda: storage)

    def _fake_download(url, dest):
        src = assets["narration"] if "narration" in url else assets["clips"][0]
        shutil.copyfile(src, dest)
        return str(dest)

    monkeypatch.setattr(video_pipeline, "_download", _fake_download)
    return storage


def test_runpod_branch_uses_provider_then_shared_ffmpeg_finalize(
    auth_client, db_session, runpod_env, monkeypatch
):
    client, headers, _ = auth_client
    calls = {}

    def _fake_generate(**kwargs):
        calls.update(kwargs)
        kwargs["on_progress"](1)
        return {"scene_count": 1, "narration_duration_seconds": 4.2}

    monkeypatch.setattr(runpod_provider, "generate", _fake_generate)
    finalize_calls = []
    real_finalize = video_pipeline._finalize
    monkeypatch.setattr(
        video_pipeline,
        "_finalize",
        lambda *a, **k: (finalize_calls.append(1), real_finalize(*a, **k)),
    )

    job_id = client.post("/videos", json=_body(), headers=headers).json()["id"]
    run_job(job_id)
    db_session.expire_all()

    final = client.get(f"/videos/{job_id}", headers=headers).json()
    assert final["status"] == "ready"
    assert finalize_calls == [1]
    assert f"videos/{job_id}.mp4" in runpod_env.uploaded
    assert calls["aspect_ratio"] == "16:9" and calls["voice_id"] == "male"
    assert calls["narration"] == SCRIPT
    assert calls["presigned_put_urls"]["clips"][0].startswith("https://r2.test/put/jobs/")
    assert "ct=audio/wav" in calls["presigned_put_urls"]["narration"]
    # Raw GPU intermediates are deleted; the final MP4 + thumbnail are kept.
    assert sorted(runpod_env.deleted) == [
        f"jobs/{job_id}/narration.wav",
        f"jobs/{job_id}/scene1.mp4",
    ]
    assert f"videos/{job_id}_thumb.jpg" in runpod_env.uploaded
    assert not any(k.startswith("videos/") for k in runpod_env.deleted)


def test_cleanup_failure_never_fails_the_job(auth_client, db_session, runpod_env, monkeypatch):
    client, headers, _ = auth_client
    monkeypatch.setattr(
        runpod_provider,
        "generate",
        lambda **kw: {"scene_count": 1, "narration_duration_seconds": 4.2},
    )

    async def _boom(key):
        raise RuntimeError("r2 down")

    monkeypatch.setattr(runpod_env, "delete", _boom)
    job_id = client.post("/videos", json=_body(), headers=headers).json()["id"]
    run_job(job_id)
    db_session.expire_all()
    assert client.get(f"/videos/{job_id}", headers=headers).json()["status"] == "ready"


def test_runpod_unavailable_fails_job_and_reverses_usage(
    auth_client, db_session, runpod_env, monkeypatch
):
    client, headers, _ = auth_client

    def _boom(**kwargs):
        raise AppError("RUNPOD_UNAVAILABLE", "Video generation is temporarily unavailable.")

    monkeypatch.setattr(runpod_provider, "generate", _boom)
    job_id = client.post("/videos", json=_body(), headers=headers).json()["id"]
    run_job(job_id)
    db_session.expire_all()

    failed = client.get(f"/videos/{job_id}", headers=headers).json()
    assert failed["status"] == "failed"
    assert client.get("/me").json()["usage"]["videosUsedToday"] == 0


def test_measured_narration_too_long_fails_with_script_too_long(
    auth_client, db_session, runpod_env, monkeypatch
):
    client, headers, _ = auth_client
    monkeypatch.setattr(
        runpod_provider,
        "generate",
        lambda **kw: {"scene_count": 1, "narration_duration_seconds": 9.0},
    )
    job_id = client.post("/videos", json=_body(), headers=headers).json()["id"]
    run_job(job_id)
    db_session.expire_all()
    failed = client.get(f"/videos/{job_id}", headers=headers).json()
    assert failed["status"] == "failed"
    assert "too long" in failed["failureReason"]


# --- runpod_provider unit tests (no network) ---


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, endpoint, timeout=10):
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class _FakeJob:
    endpoint_id = "ep"
    job_id = "j1"

    def __init__(self, responses):
        self.rp_client = _FakeClient(responses)

    def cancel(self):
        pass


def test_wait_for_result_retries_then_returns_output_and_reports_progress():
    job = _FakeJob(
        [
            ConnectionError("blip"),
            {"status": "IN_PROGRESS", "output": "scene 1/2 done"},
            {
                "status": "COMPLETED",
                "output": {"scene_count": 2, "narration_duration_seconds": 8.1},
            },
        ]
    )
    seen = []
    out = runpod_provider.wait_for_result(job, seen.append, sleep=lambda s: None)
    assert out["narration_duration_seconds"] == 8.1
    assert seen == [1]


def test_wait_for_result_exhausted_retries_raises_friendly_error():
    job = _FakeJob([ConnectionError("down")] * 4)
    with pytest.raises(AppError) as exc:
        runpod_provider.wait_for_result(job, sleep=lambda s: None)
    assert exc.value.code == "RUNPOD_UNAVAILABLE"
    assert job.rp_client.calls == 4  # 1 attempt + 3 retries


def test_worker_error_output_becomes_runpod_unavailable():
    job = _FakeJob([{"status": "COMPLETED", "output": {"error": "Upload failed"}}])
    with pytest.raises(AppError) as exc:
        runpod_provider.wait_for_result(job, sleep=lambda s: None)
    assert exc.value.code == "RUNPOD_UNAVAILABLE"
    assert "Upload failed" not in exc.value.message
