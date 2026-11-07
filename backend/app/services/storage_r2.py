import asyncio
from functools import partial

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 2
_TIMEOUT_SECONDS = 10
# Covers queue wait + MAX_PROCESSING_SECONDS (600) with wide margin; used for GET and PUT.
_PRESIGNED_URL_EXPIRY_SECONDS = 3600


class R2StorageService:
    """boto3 S3-compatible client against Cloudflare R2."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.R2_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=BotoConfig(
                signature_version="s3v4",  # R2 rejects SigV2 presigned URLs (boto3 default)
                s3={"addressing_style": "path"},
                connect_timeout=_TIMEOUT_SECONDS,
                read_timeout=_TIMEOUT_SECONDS,
                retries={"max_attempts": 0},
            ),
        )

    async def _call_with_retry(self, func, /, *args, **kwargs):
        loop = asyncio.get_running_loop()
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return await loop.run_in_executor(None, partial(func, *args, **kwargs))
            except (BotoCoreError, ClientError) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(2**attempt)
        logger.error("r2_call_failed", exc_info=last_exc)
        raise AppError(
            "STORAGE_UNAVAILABLE", "Storage is temporarily unavailable. Please try again."
        )

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        await self._call_with_retry(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get_download_url(self, key: str) -> str:
        return await self._call_with_retry(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=_PRESIGNED_URL_EXPIRY_SECONDS,
        )

    async def get_presigned_put_url(self, key: str, content_type: str) -> str:
        return await self._call_with_retry(
            self._client.generate_presigned_url,
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=_PRESIGNED_URL_EXPIRY_SECONDS,
        )

    async def delete(self, key: str) -> None:
        await self._call_with_retry(self._client.delete_object, Bucket=self._bucket, Key=key)
