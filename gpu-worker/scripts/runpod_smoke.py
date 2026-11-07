#!/usr/bin/env python3
"""Submit ONE 5-second 16:9 job straight to the RunPod endpoint (no web app, no DB).

Run with the backend virtualenv so it can reuse the app's R2 settings for presigned PUT URLs:

    cd backend && .venv/bin/python ../gpu-worker/scripts/runpod_smoke.py [--timeout 900] [--keep]

Polls GET /status every 10 s and prints status + progress. On success it downloads the
outputs from R2 to check sizes, then deletes them (unless --keep). On Ctrl-C, timeout or
failure it cancels the RunPod job (POST /cancel/{id}) so nothing runs and bills later.
The API key is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.storage_service import get_storage  # noqa: E402

API = "https://api.runpod.ai/v2"
POLL_SECONDS = 10
# Same 10-word sentence used for the preset voices (~5 s of narration at 12 words / 5 s).
NARRATION = "آج موسم بہت خوشگوار ہے اور آسمان بالکل صاف ہے۔"
PROMPT = "A teacher writing on a whiteboard in a bright classroom, students listening, cinematic"


def rp(method: str, path: str, key: str, body: dict | None = None, timeout: int = 30):
    req = urllib.request.Request(
        f"{API}/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"RunPod HTTP {e.code} on {method} {path}: {e.read().decode()[:500]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=0, help="seconds (default MAX_PROCESSING_SECONDS)")
    ap.add_argument("--keep", action="store_true", help="keep the R2 objects")
    args = ap.parse_args()

    s = get_settings()
    if not s.RUNPOD_API_KEY or not s.RUNPOD_ENDPOINT_ID:
        print("RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID missing in backend/.env", file=sys.stderr)
        return 2
    if s.STORAGE_PROVIDER != "r2":
        print("STORAGE_PROVIDER must be r2 (the worker uploads via presigned PUT URLs)", file=sys.stderr)
        return 2
    key, eid = s.RUNPOD_API_KEY, s.RUNPOD_ENDPOINT_ID
    timeout = args.timeout or s.MAX_PROCESSING_SECONDS

    storage = get_storage()
    run = f"smoke/{uuid.uuid4()}"
    clip_key, wav_key = f"{run}/scene1.mp4", f"{run}/narration.wav"

    async def presign():
        return (
            await storage.get_presigned_put_url(clip_key, "video/mp4"),
            await storage.get_presigned_put_url(wav_key, "audio/wav"),
        )

    clip_url, wav_url = asyncio.run(presign())
    payload = {
        "input": {
            "scenes": [{"visual_prompt": PROMPT, "narration": NARRATION}],
            "aspect_ratio": "16:9",
            "frames": 121,
            "voice_id": "male",
            "presigned_put_urls": {"clips": [clip_url], "narrations": [wav_url]},
        }
    }
    job_id = rp("POST", f"{eid}/run", key, payload)["id"]
    print(f"submitted job {job_id} (timeout {timeout}s)")

    start = time.monotonic()
    ok = False
    try:
        while True:
            elapsed = int(time.monotonic() - start)
            st = rp("GET", f"{eid}/status/{job_id}", key)
            status = st.get("status")
            extra = {k: st[k] for k in ("output", "stream", "delayTime", "executionTime") if k in st}
            print(f"[{elapsed:>4}s] {status}  {json.dumps(extra, ensure_ascii=False)[:400]}")
            if status == "COMPLETED":
                out = st.get("output") or {}
                if "error" in out:
                    print(f"\nWORKER ERROR (full):\n{out['error']}")
                    return 1
                print(f"\nOUTPUT: {json.dumps(out, ensure_ascii=False)}")
                ok = True
                break
            if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                print(f"\nJOB {status}. Full response:\n{json.dumps(st, indent=2, ensure_ascii=False)}")
                return 1
            if elapsed > timeout:
                print(f"\nTimed out after {timeout}s while {status}.")
                return 1
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    finally:
        if not ok:
            try:
                res = rp("POST", f"{eid}/cancel/{job_id}", key, timeout=10)
                print(f"cancelled job {job_id}: {res}")
            except BaseException as exc:  # noqa: BLE001
                print(f"WARNING: could not cancel {job_id}: {exc}")

    # Verify the uploads really landed in R2.
    async def verify():
        for k in (clip_key, wav_key):
            url = await storage.get_download_url(k)
            with urllib.request.urlopen(url, timeout=60) as r:
                print(f"  R2 {k}: {len(r.read()) / 1e6:.2f} MB")
            if not args.keep:
                await storage.delete(k)

    asyncio.run(verify())
    print("SMOKE TEST PASSED" + ("" if args.keep else " (R2 test objects deleted)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
