from pathlib import Path

from app.core.config import get_settings

STATIC_MOUNT_PATH = "/static"


class LocalStorageService:
    """Disk-backed storage under LOCAL_STORAGE_PATH, served via main.py's StaticFiles mount."""

    def __init__(self) -> None:
        settings = get_settings()
        self._root = Path(settings.LOCAL_STORAGE_PATH).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if self._root != path and self._root not in path.parents:
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def get_download_url(self, key: str) -> str:
        return f"{STATIC_MOUNT_PATH}/{key}"

    async def get_presigned_put_url(self, key: str, content_type: str) -> str:
        # No presigned-PUT concept locally; callers write directly via upload().
        return f"{STATIC_MOUNT_PATH}/{key}"

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()
