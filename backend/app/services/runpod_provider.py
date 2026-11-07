"""Backend client for the RunPod Serverless GPU worker (T089).

Submits one job (all scenes, each with its own visual prompt and narration) and polls
it to completion via the `runpod` SDK. Transient SDK/network errors are retried (3 retries, exponential
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
CANCEL_ATTEMPTS = 3
DEFAULT_FRAMES = 121

_UNAVAILABLE = "Video generation is temporarily unavailable. Please try again in a few minutes."
_FAILED = "Couldn't generate your video. Please try again."
_SCENE_RE = re.compile(r"scene\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)

ProgressCallback = Callable[[int], None]  # called with number of completed scenes
StatusCallback = Callable[[str], None]  # called on RunPod status changes: IN_QUEUE / IN_PROGRESS


def _unavailable(cause: Exception | str) -> AppError:
    logger.error(f"runpod_unavailable: {cause}")
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
    scenes: list[dict[str, str]],
    aspect_ratio: str,
    voice_id: str,
    presigned_put_urls: dict[str, Any],
    frames: int = DEFAULT_FRAMES,
):
    """Submits the job and returns the SDK Job handle.

    `scenes` = [{"visual_prompt": str, "narration": str}, ...] (one per 5 s scene);
    `presigned_put_urls` = {"clips": [url per scene], "narrations": [url per scene]}.
    """
    endpoint = _get_endpoint()
    payload = {
        "input": {
            "scenes": scenes,
            "aspect_ratio": aspect_ratio,
            "frames": frames,
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


def _cancel_quietly(job) -> None:
    """POST /v2/{endpoint}/cancel/{job_id} so an orphaned job can never run (and bill) later."""
    for attempt in range(CANCEL_ATTEMPTS):
        try:
            job.cancel()
            logger.warning(f"runpod_job_cancelled: job_id={job.job_id}")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"runpod_cancel_failed: job_id={job.job_id} attempt={attempt + 1} {exc}")
            time.sleep(1)


def wait_for_result(
    job,
    on_progress: ProgressCallback | None = None,
    timeout: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
    on_status: StatusCallback | None = None,
) -> dict:
    """Polls until the job finishes; returns the worker's output dict.

    Any exit other than success (our timeout, worker failure, polling errors, or the RQ
    job being killed) cancels the RunPod job so it cannot start later and burn GPU time.
    `on_status` gets "IN_QUEUE" while waiting for a worker and "IN_PROGRESS" once running;
    scene progress is only reported while IN_PROGRESS.
    """
    if timeout is None:
        timeout = float(get_settings().MAX_PROCESSING_SECONDS)
    deadline = time.monotonic() + timeout
    last_scene = 0
    last_status: str | None = None
    succeeded = False
    try:
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
                    logger.error(
                        f"runpod_worker_error: job_id={job.job_id} error={output['error']}"
                    )
                    raise AppError("RUNPOD_UNAVAILABLE", _FAILED)
                succeeded = True
                return output
            if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                logger.error(
                    f"runpod_job_failed: job_id={job.job_id} status={status} "
                    f"error={state.get('error') or state.get('output')}"
                )
                raise AppError("RUNPOD_UNAVAILABLE", _FAILED)
            if status != last_status:
                last_status = status
                logger.info(f"runpod_job_status: job_id={job.job_id} status={status}")
                if on_status and status in ("IN_QUEUE", "IN_PROGRESS"):
                    on_status(status)
            if status == "IN_PROGRESS":
                done = _scenes_done(state)
                if on_progress and done is not None and done > last_scene:
                    last_scene = done
                    on_progress(done)
            sleep(POLL_INTERVAL_SECONDS)

        logger.error(
            f"runpod_job_timeout: job_id={job.job_id} after {timeout:.0f}s, last={last_status}"
        )
        raise AppError("RUNPOD_UNAVAILABLE", _FAILED)
    finally:
        if not succeeded:
            _cancel_quietly(job)


def generate(
    scenes: list[dict[str, str]],
    aspect_ratio: str,
    voice_id: str,
    presigned_put_urls: dict[str, Any],
    on_progress: ProgressCallback | None = None,
    on_status: StatusCallback | None = None,
) -> dict:
    """Submit + poll. Returns {"scene_count": int, "narration_durations_seconds": [float, ...]}."""
    job = submit_job(scenes, aspect_ratio, voice_id, presigned_put_urls)
    return wait_for_result(job, on_progress, on_status=on_status)
