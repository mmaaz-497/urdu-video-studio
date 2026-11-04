import asyncio
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
SEND_TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 2  # retries after the first attempt => up to 3 attempts total
RETRY_BACKOFF_SECONDS = 0.5

_EMAIL_FAILED_MESSAGE = "We couldn't send the email right now. Please try again in a few minutes."


class EmailSender(Protocol):
    async def send_password_reset(self, to_email: str, reset_link: str) -> None: ...


def _reset_email_content(reset_link: str) -> tuple[str, str]:
    subject = "Reset your Urdu Video Studio password"
    html = (
        "<p>We received a request to reset your password.</p>"
        f'<p><a href="{reset_link}">Choose a new password</a></p>'
        "<p>This link expires in 30 minutes and can be used once. "
        "If you didn't ask for this, you can ignore this email.</p>"
    )
    return subject, html


class ResendEmailSender:
    def __init__(self, api_key: str, from_address: str) -> None:
        self._api_key = api_key
        self._from = from_address

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        subject, html = _reset_email_content(reset_link)
        payload = {"from": self._from, "to": [to_email], "subject": subject, "html": html}
        headers = {"Authorization": f"Bearer {self._api_key}"}

        last_error = "unknown"
        for attempt in range(MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS) as client:
                    resp = await client.post(RESEND_API_URL, json=payload, headers=headers)
                if resp.status_code < 300:
                    return
                last_error = f"HTTP {resp.status_code}"
                # Client errors (bad key, bad address) won't succeed on retry.
                if resp.status_code < 500 and resp.status_code != 429:
                    break
            except httpx.HTTPError as exc:
                last_error = type(exc).__name__
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

        logger.error("resend_send_failed", extra={"reason": last_error})
        raise AppError("EMAIL_SEND_FAILED", _EMAIL_FAILED_MESSAGE)


class ConsoleEmailSender:
    """Dev fallback: prints the reset link to the backend log instead of sending."""

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        logger.warning(
            "DEV EMAIL (RESEND_API_KEY not set - not actually sent) "
            f"password reset for {to_email}: {reset_link}"
        )


def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.RESEND_API_KEY:
        return ResendEmailSender(settings.RESEND_API_KEY, settings.EMAIL_FROM)
    logger.warning("RESEND_API_KEY is empty: using ConsoleEmailSender (emails are only logged)")
    return ConsoleEmailSender()
