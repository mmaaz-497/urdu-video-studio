import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.services import storage_local
from app.services.storage_local import LocalStorageService


def _service(monkeypatch, tmp_path):
    class _S:
        LOCAL_STORAGE_PATH = str(tmp_path)

    monkeypatch.setattr(storage_local, "get_settings", lambda: _S())
    return LocalStorageService()


def test_download_url_is_under_api_prefix(monkeypatch, tmp_path):
    svc = _service(monkeypatch, tmp_path)
    assert asyncio.run(svc.get_download_url("videos/abc.mp4")) == "/api/static/videos/abc.mp4"


def test_url_resolves_once_proxy_strips_api(monkeypatch, tmp_path):
    svc = _service(monkeypatch, tmp_path)
    asyncio.run(svc.upload("videos/abc.mp4", b"data", "video/mp4"))
    app = FastAPI()
    app.mount(storage_local.STATIC_MOUNT_PATH, StaticFiles(directory=str(tmp_path)))
    url = asyncio.run(svc.get_download_url("videos/abc.mp4"))
    # The frontend proxy (Next rewrite / Caddy) strips the leading /api before forwarding.
    assert url.startswith("/api/")
    resp = TestClient(app).get(url.removeprefix("/api"))
    assert resp.status_code == 200 and resp.content == b"data"
