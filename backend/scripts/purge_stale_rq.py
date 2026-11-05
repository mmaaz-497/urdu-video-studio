"""Purge stale RQ entries (queued, failed registry, started registry) whose video_jobs
row no longer exists. Usage (from backend/):  .venv/bin/python -m scripts.purge_stale_rq [--all]

--all additionally empties the whole `videos` queue and its failed registry."""
import sys
import uuid

from rq.job import Job
from rq.registry import FailedJobRegistry, StartedJobRegistry

from app.core.db import SessionLocal
from app.services import video_job_service
from app.worker import get_queue


def _row_exists(db, job: Job) -> bool:
    try:
        return video_job_service.get_job(db, uuid.UUID(str(job.args[0]))) is not None
    except (IndexError, ValueError):
        return False


def main() -> None:
    purge_all = "--all" in sys.argv
    q = get_queue()
    db = SessionLocal()
    removed = 0
    try:
        sources = {
            "queued": q.get_job_ids(),
            "failed": FailedJobRegistry(queue=q).get_job_ids(),
            "started": StartedJobRegistry(queue=q).get_job_ids(),
        }
        for where, ids in sources.items():
            for jid in ids:
                job = Job.fetch(jid, connection=q.connection)
                if purge_all or not _row_exists(db, job):
                    job.delete(remove_from_queue=True)
                    removed += 1
                    print(f"purged {where} {jid} args={job.args}")
    finally:
        db.close()
    print(f"done, purged {removed}")


if __name__ == "__main__":
    main()
