"""
QStash Service - Message queue for async task processing using Upstash QStash Queues.

This service uses QStash Queues for reliable, ordered message delivery with
configurable parallelism and automatic retries.

See: https://upstash.com/docs/qstash/features/queues
"""

import logging
from typing import Any

from qstash import QStash, Receiver

from app.core.config import settings

logger = logging.getLogger(__name__)


class QStashService:
    """
    Service for enqueuing async tasks via Upstash QStash Queues.

    Uses dedicated queues for better control, visibility, and reliability.
    """

    _client: QStash | None = None
    _receiver: Receiver | None = None
    _initialized: bool = False
    _is_local: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize the QStash client and create queues."""
        if cls._initialized:
            return

        cls._is_local = settings.is_local_qstash

        if not settings.SERVER_BASE_URL:
            logger.warning("SERVER_BASE_URL not configured - queue service disabled")
            return

        try:
            if cls._is_local:
                cls._client = QStash(
                    token=settings.QSTASH_TOKEN or "test_token",
                    base_url=settings.QSTASH_URL,
                )
                logger.info(
                    f"QStash initialized in LOCAL mode (dev server: {settings.QSTASH_URL})"
                )
            else:
                if not settings.QSTASH_TOKEN:
                    logger.error(
                        "QSTASH_TOKEN required in production - queue service disabled"
                    )
                    return

                cls._client = QStash(settings.QSTASH_TOKEN)
                logger.info("QStash initialized in PRODUCTION mode")

            # Configure signature verification
            if settings.QSTASH_CURRENT_SIGNING_KEY and settings.QSTASH_NEXT_SIGNING_KEY:
                cls._receiver = Receiver(
                    current_signing_key=settings.QSTASH_CURRENT_SIGNING_KEY,
                    next_signing_key=settings.QSTASH_NEXT_SIGNING_KEY,
                )

            # Create/update the notifications queue
            cls._setup_queues()

            cls._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize QStash: {e}")

    @classmethod
    def _setup_queues(cls) -> None:
        """Create or update queues with desired configuration."""
        if not cls._client:
            return

        try:
            queue_name = settings.QSTASH_QUEUE_NAME
            parallelism = settings.QSTASH_QUEUE_PARALLELISM
            cls._client.queue.upsert(queue_name, parallelism=parallelism)
            logger.info(f"Queue '{queue_name}' ready (parallelism={parallelism})")
        except Exception as e:
            logger.error(f"Failed to setup queue: {e}")

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
        retries: int = 3,
        deduplication_id: str | None = None,
    ) -> str | None:
        """
        Enqueue a task to the notifications queue.

        Failed messages after retries go to QStash's Dead Letter Queue (DLQ)
        which can be monitored in the Upstash dashboard.

        Args:
            endpoint: The webhook endpoint path
            payload: The JSON payload to send
            retries: Number of retry attempts (default 3, then goes to DLQ)
            deduplication_id: Optional ID to prevent duplicate messages

        Returns:
            QStash message ID or None if enqueue failed
        """
        if not cls._client:
            logger.error("QStash not initialized - cannot enqueue task")
            return None

        webhook_url = f"{settings.SERVER_BASE_URL}{endpoint}"

        try:
            queue_name = settings.QSTASH_QUEUE_NAME
            response = cls._client.message.enqueue_json(
                queue=queue_name,
                url=webhook_url,
                body=payload,
                retries=retries,
                deduplication_id=deduplication_id,
            )
            logger.info(f"Enqueued to '{queue_name}': {response.message_id}")
            return response.message_id

        except Exception as e:
            logger.error(f"Failed to enqueue: {e}")
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
