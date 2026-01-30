"""
Internal API routes for queue processing.

These endpoints are called by QStash webhooks and should NOT be exposed
to external clients. They are protected by signature verification.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import VerifiedQStashPayload, get_db
from app.models import SMSMessage
from app.services.notification_dispatcher import NotificationDispatcher

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/notifications/send")
async def process_notification(payload: VerifiedQStashPayload) -> dict[str, str]:
    """
    Process a queued notification from QStash.

    This endpoint receives notification payloads from the queue and
    routes them to the appropriate device handler.
    """
    logger.info(f"Processing notification for device {payload.get('device_id')}")

    success = await NotificationDispatcher.process_queued(payload)

    if not success:
        # Return 500 so QStash will retry
        raise HTTPException(status_code=500, detail="Failed to send notification")

    return {"status": "sent"}


@router.post("/queue/callback")
async def handle_queue_callback(payload: VerifiedQStashPayload) -> dict[str, str]:
    """
    Handle successful delivery callback from QStash.

    Called when a queued task completes successfully.
    """

    logger.info(f"Queue callback received: {payload.get('sourceMessageId', 'unknown')}")

    # Update message status if message_ids are present
    message_ids = payload.get("body", {}).get("message_ids", [])
    if message_ids:
        session = next(get_db())
        try:
            for msg_id in message_ids:
                message = session.get(SMSMessage, UUID(msg_id))
                if message and message.status == "assigned":
                    message.status = "sending"
                    session.add(message)
            session.commit()
        finally:
            session.close()

    return {"status": "acknowledged"}


@router.post("/queue/failure")
async def handle_queue_failure(payload: VerifiedQStashPayload) -> dict[str, str]:
    """
    Handle delivery failure callback from QStash.

    Called when a queued task fails after all retries.
    """

    logger.error(f"Queue delivery failed: {payload}")

    # Mark messages as failed
    body = payload.get("body", {})
    message_ids = body.get("message_ids", [])

    if message_ids:
        session = next(get_db())
        try:
            for msg_id in message_ids:
                message = session.get(SMSMessage, UUID(msg_id))
                if message:
                    message.status = "failed"
                    message.error_message = "Delivery failed after retries"
                    session.add(message)
            session.commit()
        finally:
            session.close()

    return {"status": "acknowledged"}
