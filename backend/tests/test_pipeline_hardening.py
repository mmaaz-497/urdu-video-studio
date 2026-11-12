import subprocess
import uuid

import pytest

from app.core.errors import AppError
from app.services import ffmpeg_service, video_pipeline


def test_ffmpeg_never_inherits_terminal_stdin(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(ffmpeg_service.subprocess, "run", fake_run)
    ffmpeg_service._run(["ffmpeg", "-y", "-i", "a", "b"])
    assert seen["cmd"][:2] == ["ffmpeg", "-nostdin"]
    # Thread cap (shared VPS): per-output -threads sits right before the output path.
    assert seen["cmd"][-3:] == ["-threads", "2", "b"]
    assert seen["cmd"][seen["cmd"].index("-i") - 2 :][:4] == ["-threads", "2", "-i", "a"]
    assert seen["cmd"][seen["cmd"].index("-filter_complex_threads") + 1] == "2"
    assert seen["kw"]["stdin"] == subprocess.DEVNULL
    assert seen["kw"]["start_new_session"] is True
    assert seen["kw"]["timeout"] == ffmpeg_service.FFMPEG_TIMEOUT_SECONDS


def test_storage_call_times_out_with_friendly_error():
    import asyncio

    async def hang():
        await asyncio.sleep(10)

    with pytest.raises(AppError) as ei:
        video_pipeline._storage_call(hang(), timeout=0.1)
    assert ei.value.code == "STORAGE_UNAVAILABLE"


def test_missing_job_row_is_discarded_and_logged(monkeypatch, caplog):
    monkeypatch.setattr(video_pipeline.video_job_service, "get_job", lambda db, jid: None)
    with caplog.at_level("ERROR"):
        result = video_pipeline.run_job(str(uuid.uuid4()))
    assert result == "discarded:video_job_not_found"
