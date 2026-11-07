import uuid
from unittest.mock import AsyncMock

import pytest
import redis as redis_sync

from app.core.config import get_settings
from app.core.errors import AppError
from app.services import llm_service, moderation_service
from app.services.llm_service import SceneOutput, ScriptGenerationOutput

VALID_SCRIPT = " ".join(["لفظ"] * 11)  # 11 "words" -> under the 1-scene (5s) 12-word hard limit
OVER_LIMIT_SCRIPT = " ".join(["لفظ"] * 20)  # 20 "words" -> over the 1-scene (5s) 12-word hard limit


def _scene(narration: str = VALID_SCRIPT, visual: str = "A student writing notes in a classroom"):
    return SceneOutput(visual_prompt=visual, narration_ur=narration)


def _body(**overrides) -> dict:
    body = {
        "idempotencyKey": str(uuid.uuid4()),
        "idea": "mujhe aik acha sa idea chahiye is topic per",
        "durationSeconds": 5,
        "aspectRatio": "16:9",
        "voiceId": "male",
    }
    body.update(overrides)
    return body


class _FakeResult:
    def __init__(self, output: ScriptGenerationOutput) -> None:
        self.final_output = output


def _valid_output() -> ScriptGenerationOutput:
    return ScriptGenerationOutput(
        corrected_idea="مجھے اس موضوع پر ایک اچھا آئیڈیا چاہیے",
        title="Test Video",
        scenes=[_scene()],
    )


def _invalid_output() -> ScriptGenerationOutput:
    # 2 scenes for a 5s (1-scene) request -> fails server-side scene-count recheck.
    return ScriptGenerationOutput(
        corrected_idea="مجھے اس موضوع پر ایک اچھا آئیڈیا چاہیے",
        title="Test Video",
        scenes=[_scene(), _scene()],
    )


@pytest.fixture(autouse=True)
def _no_real_moderation_calls(monkeypatch):
    """Every test in this file mocks the OpenAI client; none should hit the
    network. Individual tests override this where they need flagged/failed
    moderation behavior."""
    monkeypatch.setattr(moderation_service, "check_idea", AsyncMock(return_value=None))


def test_valid_structured_output_accepted(auth_client, monkeypatch):
    client, headers, _student = auth_client
    monkeypatch.setattr(
        llm_service.Runner, "run", AsyncMock(return_value=_FakeResult(_valid_output()))
    )

    resp = client.post("/scripts", json=_body(), headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["correctedIdea"] == "مجھے اس موضوع پر ایک اچھا آئیڈیا چاہیے"
    assert body["scenes"] == [
        {"visualPrompt": "A student writing notes in a classroom", "narrationUr": VALID_SCRIPT}
    ]
    assert body["urduScript"] == VALID_SCRIPT  # joined narrations, kept for display
    assert body["wordCount"] == 11
    assert body["wordLimit"] == 12
    assert body["sceneWordLimit"] == 12


def test_invalid_output_retries_once_then_fails(auth_client, monkeypatch):
    client, headers, _student = auth_client
    run_mock = AsyncMock(return_value=_FakeResult(_invalid_output()))
    monkeypatch.setattr(llm_service.Runner, "run", run_mock)

    resp = client.post("/scripts", json=_body(), headers=headers)

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "SCRIPT_GENERATION_FAILED"
    assert run_mock.await_count == 2  # exactly one retry


def test_mixed_script_idea_retries_once_then_succeeds(auth_client, monkeypatch):
    client, headers, _student = auth_client
    mixed_output = ScriptGenerationOutput(
        corrected_idea="Mera idea hai ke یہ ایک ویڈیو ہے",  # 3 Latin words -> over allowance
        title="Test Video",
        scenes=[_scene()],
    )
    run_mock = AsyncMock(side_effect=[_FakeResult(mixed_output), _FakeResult(_valid_output())])
    monkeypatch.setattr(llm_service.Runner, "run", run_mock)

    resp = client.post("/scripts", json=_body(), headers=headers)

    assert resp.status_code == 201
    assert resp.json()["correctedIdea"] == "مجھے اس موضوع پر ایک اچھا آئیڈیا چاہیے"
    assert run_mock.await_count == 2


def test_mixed_script_idea_still_mixed_after_retry_fails(auth_client, monkeypatch):
    client, headers, _student = auth_client
    mixed_output = ScriptGenerationOutput(
        corrected_idea="Mera idea hai ke یہ ایک ویڈیو ہے",
        title="Test Video",
        scenes=[_scene()],
    )
    run_mock = AsyncMock(return_value=_FakeResult(mixed_output))
    monkeypatch.setattr(llm_service.Runner, "run", run_mock)

    resp = client.post("/scripts", json=_body(), headers=headers)

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "SCRIPT_GENERATION_FAILED"
    assert run_mock.await_count == 2


def test_moderation_flagged_idea_short_circuits(auth_client, monkeypatch):
    client, headers, _student = auth_client
    monkeypatch.setattr(
        moderation_service,
        "check_idea",
        AsyncMock(side_effect=AppError("UNSAFE_CONTENT", "This idea can't be used.")),
    )
    run_mock = AsyncMock(return_value=_FakeResult(_valid_output()))
    monkeypatch.setattr(llm_service.Runner, "run", run_mock)

    resp = client.post("/scripts", json=_body(), headers=headers)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "UNSAFE_CONTENT"
    run_mock.assert_not_awaited()


def test_replay_with_same_idempotency_key_after_completion_returns_cached(auth_client, monkeypatch):
    client, headers, student = auth_client
    monkeypatch.setattr(
        llm_service.Runner, "run", AsyncMock(return_value=_FakeResult(_valid_output()))
    )
    body = _body()

    first = client.post("/scripts", json=body, headers=headers)
    assert first.status_code == 201

    usage_after_first = client.get("/me").json()["usage"]["scriptsUsedToday"]

    second = client.post("/scripts", json=body, headers=headers)
    assert second.status_code == 201
    assert second.json() == first.json()

    usage_after_second = client.get("/me").json()["usage"]["scriptsUsedToday"]
    assert usage_after_second == usage_after_first


def test_over_limit_output_is_trimmed_not_failed(auth_client, monkeypatch):
    """SC-003: the Review screen must never receive an unapprovable script —
    if the model is still over the hard word limit after one retry, the
    backend trims it server-side instead of surfacing an error."""
    client, headers, _student = auth_client
    over_limit_output = ScriptGenerationOutput(
        corrected_idea="مجھے اس موضوع پر ایک اچھا آئیڈیا چاہیے",
        title="Test Video",
        scenes=[_scene(OVER_LIMIT_SCRIPT)],
    )
    run_mock = AsyncMock(return_value=_FakeResult(over_limit_output))
    monkeypatch.setattr(llm_service.Runner, "run", run_mock)

    resp = client.post("/scripts", json=_body(), headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["wordCount"] <= body["sceneWordLimit"]
    assert run_mock.await_count == 2  # one retry attempted before trimming


def test_scene_prompts_strip_on_screen_text_requests(auth_client, monkeypatch):
    client, headers, _student = auth_client
    output_with_overlay = ScriptGenerationOutput(
        corrected_idea="مجھے اس موضوع پر ایک اچھا آئیڈیا چاہیے",
        title="Test Video",
        scenes=[_scene(visual='A classroom; overlay text: "Save Water" is shown on screen')],
    )
    monkeypatch.setattr(
        llm_service.Runner, "run", AsyncMock(return_value=_FakeResult(output_with_overlay))
    )

    resp = client.post("/scripts", json=_body(), headers=headers)

    assert resp.status_code == 201
    scene = resp.json()["scenes"][0]["visualPrompt"]
    assert "overlay" not in scene.lower()
    assert "Save Water" not in scene


def test_concurrent_duplicate_while_pending_gets_425(auth_client):
    client, headers, student = auth_client
    body = _body()

    sync_redis = redis_sync.Redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    pending_key = f"script-idem:{student.id}:{body['idempotencyKey']}"
    sync_redis.set(pending_key, "pending", ex=30)

    usage_before = client.get("/me").json()["usage"]["scriptsUsedToday"]

    resp = client.post("/scripts", json=body, headers=headers)

    assert resp.status_code == 425
    assert resp.json()["error"]["code"] == "REQUEST_IN_PROGRESS"

    usage_after = client.get("/me").json()["usage"]["scriptsUsedToday"]
    assert usage_after == usage_before

    sync_redis.delete(pending_key)


def test_over_limit_scene_is_trimmed_per_scene_and_retry_names_the_scene(auth_client, monkeypatch):
    """The limit is per scene: only the offending scene is trimmed, the other is untouched,
    and the retry feedback tells the model which scene was too long."""
    client, headers, _student = auth_client
    output = ScriptGenerationOutput(
        corrected_idea="مجھے اس موضوع پر ایک اچھا آئیڈیا چاہیے",
        title="Test Video",
        scenes=[_scene(VALID_SCRIPT), _scene(OVER_LIMIT_SCRIPT)],
    )
    run_mock = AsyncMock(return_value=_FakeResult(output))
    monkeypatch.setattr(llm_service.Runner, "run", run_mock)

    resp = client.post("/scripts", json=_body(durationSeconds=10), headers=headers)

    assert resp.status_code == 201
    scenes = resp.json()["scenes"]
    assert scenes[0]["narrationUr"] == VALID_SCRIPT
    assert len(scenes[1]["narrationUr"].split()) == 12
    assert "Scene 2" in run_mock.await_args_list[1].args[1]
    assert "Scene 1" not in run_mock.await_args_list[1].args[1]
