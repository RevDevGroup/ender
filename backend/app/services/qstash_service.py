"""
QStash Service - Generic message queue for async task processing.

This service provides a decoupled way to enqueue tasks that will be
processed asynchronously via webhooks. It supports any type of task,
not just FCM notifications.

QStash is ALWAYS required:
- In production: Uses Upstash QStash cloud service
- In local development: Uses QStash CLI dev server (npx @upstash/qstash-cli dev)

See: https://upstash.com/docs/qstash/howto/local-development
"""

import logging
from typing import Any

from qstash import QStash, Receiver

from app.core.config import settings

logger = logging.getLogger(__name__)


class QStashService:
    """
    Generic service for enqueuing async tasks via Upstash QStash.

    QStash is always required for message queue functionality.
    In local development, run the QStash CLI dev server:
        npx @upstash/qstash-cli dev

    The dev server provides test tokens automatically.
    """

    _client: QStash | None = None
    _receiver: Receiver | None = None
    _initialized: bool = False
    _is_local: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize the QStash client."""
        if cls._initialized:
            return

        cls._is_local = settings.is_local_qstash

        if not settings.SERVER_BASE_URL:
            logger.warning("SERVER_BASE_URL not configured - queue service disabled")
            return

        try:
            if cls._is_local:
                # Local development: use QStash CLI dev server
                # The dev server generates test tokens automatically
                # Run: npx @upstash/qstash-cli dev
                cls._client = QStash(
                    token=settings.QSTASH_TOKEN or "test_token",
                    base_url=settings.QSTASH_URL,
                )
                logger.info(
                    f"QStash initialized in LOCAL mode (dev server: {settings.QSTASH_URL})"
                )
            else:
                # Production: requires real QStash token
                if not settings.QSTASH_TOKEN:
                    logger.error(
                        "QSTASH_TOKEN required in production - queue service disabled"
                    )
                    return

                cls._client = QStash(settings.QSTASH_TOKEN)
                logger.info("QStash initialized in PRODUCTION mode")

            # Configure signature verification (optional in local, required in prod)
            if settings.QSTASH_CURRENT_SIGNING_KEY and settings.QSTASH_NEXT_SIGNING_KEY:
                cls._receiver = Receiver(
                    current_signing_key=settings.QSTASH_CURRENT_SIGNING_KEY,
                    next_signing_key=settings.QSTASH_NEXT_SIGNING_KEY,
                )

            cls._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize QStash: {e}")

    @classmethod
    def is_available(cls) -> bool:
        """Check if QStash is configured and available."""
        return cls._client is not None

    @classmethod
    def enqueue(
        cls,
        endpoint: str,
        payload: dict[str, Any],
        *,
        retries: int = 5,
        delay: str | None = None,
        deduplication_id: str | None = None,
    ) -> str | None:
        """
        Enqueue a task for async processing.

        Args:
            endpoint: The webhook endpoint path (e.g., "/api/v1/internal/fcm-send")
            payload: The JSON payload to send
            retries: Number of retry attempts on failure
            delay: Optional delay before processing (e.g., "10s", "1m")
            deduplication_id: Optional ID to prevent duplicate messages

        Returns:
            QStash message ID or None if enqueue failed
        """
        if not cls._client:
            logger.error("QStash not initialized - cannot enqueue task")
            return None

        webhook_url = f"{settings.SERVER_BASE_URL}{endpoint}"
        callback_base = f"{settings.SERVER_BASE_URL}/api/v1/internal/queue"

        try:
            kwargs: dict[str, Any] = {
                "url": webhook_url,
                "body": payload,
                "retries": retries,
                "callback": f"{callback_base}/callback",
                "failure_callback": f"{callback_base}/failure",
            }

            if delay:
                kwargs["delay"] = delay

            if deduplication_id:
                kwargs["deduplication_id"] = deduplication_id

            response = cls._client.message.publish_json(**kwargs)
            logger.info(f"Task enqueued: {response.message_id} -> {endpoint}")
            return response.message_id

        except Exception as e:
            logger.error(f"Failed to enqueue task to {endpoint}: {e}")
            return None

    @classmethod
    def verify_signature(cls, body: bytes, signature: str, url: str) -> bool:
        """
        Verify a QStash webhook signature.

        Args:
            body: Raw request body bytes
            signature: Upstash-Signature header value
            url: Full webhook URL

        Returns:
            True if signature is valid, False otherwise
        """
        # Skip verification in local development (QStash CLI uses its own keys)
        if cls._is_local:
            logger.debug("Skipping QStash signature verification in local mode")
            return True

        if not cls._receiver:
            logger.warning("QStash receiver not configured - skipping verification")
            return True

        try:
            cls._receiver.verify(body=body, signature=signature, url=url)
            return True
        except Exception as e:
            logger.warning(f"Invalid QStash signature: {e}")
            return False
