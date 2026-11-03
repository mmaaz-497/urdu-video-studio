from typing import Protocol, runtime_checkable

from app.core.config import get_settings


@runtime_checkable
class StorageService(Protocol):
    async def upload(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get_download_url(self, key: str) -> str: ...

    async def get_presigned_put_url(self, key: str, content_type: str) -> str: ...

    async def delete(self, key: str) -> None: ...


def get_storage() -> StorageService:
    settings = get_settings()
    if settings.STORAGE_PROVIDER == "r2":
        from app.services.storage_r2 import R2StorageService

        return R2StorageService()

    from app.services.storage_local import LocalStorageService

    return LocalStorageService()
