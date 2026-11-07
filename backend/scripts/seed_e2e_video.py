"""Seed a throwaway student + a READY video (mock pipeline) for the Playwright download check.

Usage (from backend/):  .venv/bin/python -m scripts.seed_e2e_video [--aspect 16:9|9:16]
Uses whatever STORAGE_PROVIDER the env selects (r2 = the real cross-origin case), forces the
mock video provider, and prints JSON: {"email","password","videoId"}.
"""
import argparse
import json
import os
import tempfile
import uuid
from pathlib import Path

os.environ["VIDEO_PROVIDER"] = "mock"

from app.core.db import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.student import Student  # noqa: E402
from app.models.video_job import VideoJob  # noqa: E402
from app.services import mock_provider, video_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aspect", choices=["16:9", "9:16"], default="16:9")
    args = parser.parse_args()

    email, password = f"e2e-{uuid.uuid4().hex[:8]}@example.com", uuid.uuid4().hex
    db = SessionLocal()
    try:
        student = Student(email=email, password_hash=hash_password(password))
        db.add(student)
        db.flush()
        job = VideoJob(
            student_id=student.id,
            idempotency_key=str(uuid.uuid4()),
            raw_idea="e2e",
            corrected_idea="e2e",
            title="E2E",
            urdu_script="لفظ",
            scenes=[{"visualPrompt": "A classroom", "narrationUr": "لفظ"}],
            duration_seconds=5,
            aspect_ratio=args.aspect,
            voice_id="male",
            progress_total_scenes=1,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        assets = mock_provider.pick_assets(job.aspect_ratio, 1, job.voice_id)
        with tempfile.TemporaryDirectory() as tmp:
            video_pipeline._finalize(db, job, assets["clips"], assets["narrations"], Path(tmp))
        print(json.dumps({"email": email, "password": password, "videoId": str(job.id)}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
