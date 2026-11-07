#!/usr/bin/env python3
"""Diagnose R2 upload failures without the GPU.

Run with the backend virtualenv:

    cd backend && .venv/bin/python ../gpu-worker/scripts/check_r2_upload.py

1. Builds a presigned PUT URL with the exact backend code (R2StorageService) and PUTs a
   small file with the same method/headers handler.py uses. Prints status + full body.
2. Direct boto3 put_object / head_object / delete_object with the same credentials.
3. Deletes the test objects. Secrets are never printed (URL query string is redacted).
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.storage_r2 import R2StorageService  # noqa: E402


def redact(url: str) -> str:
    p = urlsplit(url)
    params = [kv.split("=")[0] for kv in p.query.split("&")]
    return f"{p.scheme}://{p.netloc}{p.path}?<{', '.join(params)}>"


def main() -> int:
    s = get_settings()
    missing = [k for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
               if not getattr(s, k)]
    if missing:
        print(f"missing in backend/.env: {missing}", file=sys.stderr)
        return 2
    print(f"bucket={s.R2_BUCKET} endpoint=https://{s.R2_ACCOUNT_ID[:4]}…r2.cloudflarestorage.com")

    svc = R2StorageService()
    client = svc._client
    bucket = s.R2_BUCKET
    run = uuid.uuid4().hex[:8]
    presigned_key = f"jobs/_diag/{run}-presigned.wav"
    direct_key = f"jobs/_diag/{run}-direct.wav"
    body = b"RIFF-test-" + b"0" * 64
    content_type = "audio/wav"
    created: list[str] = []
    rc = 0

    print("\n== 1. presigned PUT (backend code, handler.py method/headers) ==")
    url = asyncio.run(svc.get_presigned_put_url(presigned_key, content_type))
    print("url:", redact(url))
    q = urlsplit(url).query
    print("signed headers:", [kv for kv in q.split("&") if kv.startswith("X-Amz-SignedHeaders")])
    r = requests.put(url, data=body, headers={"Content-Type": content_type}, timeout=30)
    print("status:", r.status_code)
    print("body:", r.text or "<empty>")
    if r.ok:
        created.append(presigned_key)
    else:
        rc = 1

    print("\n== 2. direct boto3 with same credentials ==")
    for name, fn in (
        ("put_object", lambda: client.put_object(Bucket=bucket, Key=direct_key, Body=body,
                                                 ContentType=content_type)),
        ("head_object", lambda: client.head_object(Bucket=bucket, Key=direct_key)),
    ):
        try:
            fn()
            print(f"{name}: OK")
            if name == "put_object":
                created.append(direct_key)
        except Exception as exc:  # noqa: BLE001
            resp = getattr(exc, "response", {}) or {}
            err = resp.get("Error", {})
            print(f"{name}: FAILED {err.get('Code')} {err.get('Message')} "
                  f"(http {resp.get('ResponseMetadata', {}).get('HTTPStatusCode')})")
            rc = 1

    print("\n== 3. cleanup ==")
    for key in created:
        try:
            client.delete_object(Bucket=bucket, Key=key)
            print(f"delete_object {key}: OK")
        except Exception as exc:  # noqa: BLE001
            err = (getattr(exc, "response", {}) or {}).get("Error", {})
            print(f"delete_object {key}: FAILED {err.get('Code')} {err.get('Message')}")
            rc = 1
    print("\nRESULT:", "all OK" if rc == 0 else "FAILURES above")
    return rc


if __name__ == "__main__":
    sys.exit(main())
