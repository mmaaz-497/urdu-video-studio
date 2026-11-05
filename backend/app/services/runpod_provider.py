"""Backend client for the RunPod Serverless GPU worker (T089).

Submits one job (all scenes + narration) and polls it to completion via the
`runpod` SDK. Transient SDK/network errors are retried (3 retries, exponential
backoff, 30s request timeout); on exhaustion we raise a friendly
AppError("RUNPOD_UNAVAILABLE") and log the real cause.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

REQUEST_TIMEOUT_SECONDS = 30  # connect/read timeout per RunPod API call
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0
POLL_INTERVAL_SECONDS = 3.0
JOB_TIMEOUT_SECONDS = 1200
DEFAULT_FRAMES = 121

_UNAVAILABLE = "Video generation is temporarily unavailable. Please try again in a few minutes."
_FAILED = "Couldn't generate your video. Please try again."
_SCENE_RE = re.compile(r"scene\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)

ProgressCallback = Callable[[int], None]  # called with number of completed scenes


def _unavailable(cause: Exception | str) -> AppError:
    logger.error("runpod_unavailable", extra={"cause": str(cause)})
    return AppError("RUNPOD_UNAVAILABLE", _UNAVAILABLE)


def _with_retries(func: Callable[[], Any], sleep: Callable[[float], None] = time.sleep) -> Any:
    last: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001 - SDK raises requests/RuntimeError variants
            last = exc
            if attempt < MAX_RETRIES:
                sleep(BACKOFF_BASE_SECONDS * (2**attempt))
    raise _unavailable(last)  # type: ignore[arg-type]


def _get_endpoint():
    settings = get_settings()
    if not settings.RUNPOD_API_KEY or not settings.RUNPOD_ENDPOINT_ID:
        raise _unavailable("RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID not configured")
    import runpod

    runpod.api_key = settings.RUNPOD_API_KEY
    return runpod.Endpoint(settings.RUNPOD_ENDPOINT_ID)


def submit_job(
    scenes: list[str],
    aspect_ratio: str,
    narration: str,
    voice_id: str,
    presigned_put_urls: dict[str, Any],
    frames: int = DEFAULT_FRAMES,
):
    """Submits the job and returns the SDK Job handle.

    `presigned_put_urls` = {"clips": [url per scene], "narration": url}.
    """
    endpoint = _get_endpoint()
    payload = {
        "input": {
            "scenes": scenes,
            "aspect_ratio": aspect_ratio,
            "frames": frames,
            "narration": narration,
            "voice_id": voice_id,
            "presigned_put_urls": presigned_put_urls,
        }
    }

    def _submit():
        from runpod.endpoint.runner import Job

        resp = endpoint.rp_client.post(
            f"{endpoint.endpoint_id}/run", payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
        return Job(endpoint.endpoint_id, resp["id"], endpoint.rp_client)

    return _with_retries(_submit)


def _scenes_done(state: dict) -> int | None:
    """Best-effort parse of the worker's 'scene i/N done' progress messages."""
    found = _SCENE_RE.findall(str(state.get("output", "")) + str(state.get("stream", "")))
    return max((int(i) for i, _ in found), default=None)


def wait_for_result(
    job,
    on_progress: ProgressCallback | None = None,
    timeout: float = JOB_TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Polls until the job finishes; returns the worker's output dict."""
    deadline = time.monotonic() + timeout
    last_scene = 0
    while time.monotonic() < deadline:
        state = _with_retries(
            lambda: job.rp_client.get(
                f"{job.endpoint_id}/status/{job.job_id}", timeout=REQUEST_TIMEOUT_SECONDS
            ),
            sleep,
        )
        status = state.get("status")
        if status == "COMPLETED":
            output = state.get("output") or {}
            if "error" in output:
                logger.error("runpod_worker_error", extra={"error": output["error"]})
                raise AppError("RUNPOD_UNAVAILABLE", _FAILED)
            return output
        if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            logger.error(
                "runpod_job_failed", extra={"status": status, "detail": state.get("error")}
            )
            raise AppError("RUNPOD_UNAVAILABLE", _FAILED)
        done = _scenes_done(state)
        if on_progress and done is not None and done > last_scene:
            last_scene = done
            on_progress(done)
        sleep(POLL_INTERVAL_SECONDS)

    try:
        job.cancel()
    except Exception:  # noqa: BLE001
        logger.warning("runpod_cancel_failed")
    raise AppError("RUNPOD_UNAVAILABLE", _FAILED)


def generate(
    scenes: list[str],
    aspect_ratio: str,
    narration: str,
    voice_id: str,
    presigned_put_urls: dict[str, Any],
    on_progress: ProgressCallback | None = None,
) -> dict:
    """Submit + poll. Returns {"scene_count": int, "narration_duration_seconds": float}."""
    job = submit_job(scenes, aspect_ratio, narration, voice_id, presigned_put_urls)
    return wait_for_result(job, on_progress)
