import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import urlencode

from app.core.config import get_settings

# Where the backend mounts the files. The frontend proxy (Next.js rewrite in dev, Caddy in
# prod) strips the leading /api before forwarding, so the backend still sees /static.
STATIC_MOUNT_PATH = "/static"
# What the browser is given: same-origin under /api so the existing /api/* proxy rule covers it.
PUBLIC_URL_PREFIX = "/api" + STATIC_MOUNT_PATH


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
        return f"{PUBLIC_URL_PREFIX}/{key}"

    def _sign(self, key: str, filename: str, exp: int) -> str:
        secret = get_settings().SESSION_COOKIE_SECRET.encode()
        msg = f"{key}\n{filename}\n{exp}".encode()
        return hmac.new(secret, msg, hashlib.sha256).hexdigest()

    async def get_attachment_url(self, key: str, filename: str, expires_in: int) -> str:
        # Local disk has no presigning: emulate it with an HMAC-signed, expiring URL served
        # by the backend's /downloads/local route (same-origin under /api, like the static files).
        self._resolve(key)  # reject traversal early
        exp = int(time.time()) + expires_in
        query = urlencode({"key": key, "filename": filename, "exp": exp,
                           "sig": self._sign(key, filename, exp)})
        return f"/api/downloads/local?{query}"

    def verify_attachment(self, key: str, filename: str, exp: int, sig: str) -> Path | None:
        """Returns the file path if the signature is valid, unexpired and the file exists."""
        if exp < time.time() or not hmac.compare_digest(sig, self._sign(key, filename, exp)):
            return None
        path = self._resolve(key)
        return path if path.is_file() else None

    async def get_presigned_put_url(self, key: str, content_type: str) -> str:
        # No presigned-PUT concept locally; callers write directly via upload().
        return f"{PUBLIC_URL_PREFIX}/{key}"

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()
