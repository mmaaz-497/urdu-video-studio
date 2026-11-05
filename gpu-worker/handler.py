"""RunPod Serverless handler: Wan 2.2 TI2V-5B scenes (ComfyUI) + OmniVoice Urdu narration.

Job input (built by backend/app/services/runpod_provider.py):
{
  "scenes": ["english prompt", ...],           # 1-3 prompts
  "aspect_ratio": "16:9" | "9:16",
  "narration": "<Urdu script>",
  "voice_id": "male" | "female",
  "seed": 123,                                  # optional
  "presigned_put_urls": {
      "clips": ["https://...", ...],            # one per scene, Content-Type video/mp4
      "narration": "https://..."                # Content-Type audio/wav
  }
}
Job output:
  {"scene_count": N, "narration_duration_seconds": float}
On failure returns {"error": "<message>"} (RunPod marks the job FAILED) rather than crashing.
"""

from __future__ import annotations

import copy
import json
import os
import random
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

import requests
import runpod

COMFY_DIR = os.environ.get("COMFYUI_DIR", "/comfyui")
COMFY_HOST, COMFY_PORT = "127.0.0.1", 8188
COMFY_URL = f"http://{COMFY_HOST}:{COMFY_PORT}"
EXTRA_PATHS = os.environ.get("EXTRA_MODEL_PATHS", "/app/extra_model_paths.yaml")
WORKFLOW_PATH = Path(
    os.environ.get("WORKFLOW_PATH", Path(__file__).parent / "workflows" / "wan22_ti2v5b.json")
)

RESOLUTIONS = {"16:9": (1280, 704), "9:16": (704, 1280)}
FRAMES = 121  # @ 24 fps ~ 5 s
FPS = 24
MAX_SCENES = 3

COMFY_STARTUP_TIMEOUT = 300
SCENE_TIMEOUT = 900
PUT_TIMEOUT = 30
PUT_RETRIES = 2  # retries after the first attempt

_comfy_proc: subprocess.Popen | None = None


class JobError(Exception):
    """Job-level failure surfaced as {"error": ...} instead of crashing the worker."""


# ---------------------------------------------------------------- ComfyUI
def start_comfyui() -> None:
    global _comfy_proc
    if _comfy_proc is not None and _comfy_proc.poll() is None:
        return
    _comfy_proc = subprocess.Popen(
        [
            "python",
            "main.py",
            "--listen",
            COMFY_HOST,
            "--port",
            str(COMFY_PORT),
            "--extra-model-paths-config",
            EXTRA_PATHS,
            "--disable-auto-launch",
        ],
        cwd=COMFY_DIR,
    )
    deadline = time.time() + COMFY_STARTUP_TIMEOUT
    while time.time() < deadline:
        if _comfy_proc.poll() is not None:
            raise JobError("ComfyUI exited during startup")
        try:
            if requests.get(f"{COMFY_URL}/system_stats", timeout=2).ok:
                return
        except requests.RequestException:
            time.sleep(1)
    raise JobError("ComfyUI did not become ready in time")


def build_workflow(prompt: str, width: int, height: int, frames: int, seed: int) -> dict:
    wf = {k: v for k, v in json.loads(WORKFLOW_PATH.read_text("utf-8")).items() if k != "_meta"}
    wf = copy.deepcopy(wf)
    wf["6"]["inputs"]["text"] = prompt
    wf["55"]["inputs"].update(width=width, height=height, length=frames)
    wf["3"]["inputs"]["seed"] = seed
    wf["57"]["inputs"]["fps"] = float(FPS)
    return wf


def _find_video(outputs: dict) -> dict | None:
    for node_out in outputs.values():
        for items in node_out.values():
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and str(it.get("filename", "")).lower().endswith(
                        (".mp4", ".webm")
                    ):
                        return it
    return None


def render_scene(
    prompt: str, width: int, height: int, seed: int, out_path: Path, frames: int = FRAMES
) -> None:
    wf = build_workflow(prompt, width, height, frames, seed)
    resp = requests.post(f"{COMFY_URL}/prompt", json={"prompt": wf}, timeout=30)
    if not resp.ok:
        raise JobError(f"ComfyUI rejected the workflow: {resp.text[:500]}")
    prompt_id = resp.json()["prompt_id"]

    deadline = time.time() + SCENE_TIMEOUT
    while time.time() < deadline:
        hist = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=30).json()
        entry = hist.get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise JobError("ComfyUI reported an error generating a scene")
            video = _find_video(entry.get("outputs", {}))
            if video:
                q = urllib.parse.urlencode(
                    {
                        "filename": video["filename"],
                        "subfolder": video.get("subfolder", ""),
                        "type": video.get("type", "output"),
                    }
                )
                with requests.get(f"{COMFY_URL}/view?{q}", stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
                return
        time.sleep(2)
    raise JobError("Timed out generating a scene")


def free_comfy_memory() -> None:
    try:
        requests.post(
            f"{COMFY_URL}/free", json={"unload_models": True, "free_memory": True}, timeout=10
        )
    except requests.RequestException:
        pass


# ---------------------------------------------------------------- uploads
def put_file(url: str, path: Path, content_type: str) -> None:
    last: Exception | None = None
    for attempt in range(PUT_RETRIES + 1):
        try:
            with open(path, "rb") as f:
                r = requests.put(
                    url, data=f, headers={"Content-Type": content_type}, timeout=PUT_TIMEOUT
                )
            if r.ok:
                return
            last = RuntimeError(f"HTTP {r.status_code}")
        except requests.RequestException as exc:
            last = exc
        if attempt < PUT_RETRIES:
            time.sleep(2**attempt)
    raise JobError(f"Upload failed after {PUT_RETRIES + 1} attempts: {last}")


# ---------------------------------------------------------------- handler
def _validate(inp: dict) -> tuple[list[str], tuple[int, int], dict]:
    scenes = inp.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= MAX_SCENES:
        raise JobError(f"scenes must be a list of 1-{MAX_SCENES} prompts")
    if inp.get("aspect_ratio") not in RESOLUTIONS:
        raise JobError("aspect_ratio must be '16:9' or '9:16'")
    urls = inp.get("presigned_put_urls") or {}
    if len(urls.get("clips", [])) != len(scenes) or not urls.get("narration"):
        raise JobError("presigned_put_urls must hold one clip URL per scene plus narration")
    if not inp.get("narration") or inp.get("voice_id") not in ("male", "female"):
        raise JobError("narration text and voice_id (male|female) are required")
    return scenes, RESOLUTIONS[inp["aspect_ratio"]], urls


def handler(job: dict) -> dict:
    try:
        inp = job.get("input") or {}
        scenes, (width, height), urls = _validate(inp)
        frames = int(inp.get("frames", FRAMES))
        seed = int(inp.get("seed", random.randint(0, 2**31 - 1)))

        start_comfyui()
        with tempfile.TemporaryDirectory(prefix="job-") as tmp:
            tmp_dir = Path(tmp)
            clip_paths: list[Path] = []
            for i, prompt in enumerate(scenes):
                clip = tmp_dir / f"scene{i + 1}.mp4"
                render_scene(prompt, width, height, seed + i, clip, frames)
                clip_paths.append(clip)
                runpod.serverless.progress_update(job, f"scene {i + 1}/{len(scenes)} done")

            # Release ComfyUI's VRAM before loading the TTS model.
            free_comfy_memory()
            from tts_omnivoice.infer import release_model, synthesize

            try:
                narration = synthesize(
                    inp["narration"], inp["voice_id"], str(tmp_dir / "narration.wav")
                )
            finally:
                release_model()
            runpod.serverless.progress_update(job, "narration done")

            for clip, url in zip(clip_paths, urls["clips"], strict=True):
                put_file(url, clip, "video/mp4")
            put_file(urls["narration"], Path(narration.wav_path), "audio/wav")

        return {
            "scene_count": len(scenes),
            "narration_duration_seconds": narration.duration_seconds,
        }
    except JobError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - never crash the worker; report job-level failure
        return {"error": f"Unexpected worker error: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
