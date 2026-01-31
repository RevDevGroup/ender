"""
Internal API routes for queue processing.

Single endpoint called by QStash queue. Failed messages go to QStash DLQ.
Protected by signature verification.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.api.deps import VerifiedQStashPayload
from app.services.notification_dispatcher import NotificationDispatcher

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/notifications/send")
async def process_notification(payload: VerifiedQStashPayload) -> dict[str, str]:
    """
    Process a queued notification from QStash.

    On success: returns 200, message delivered to FCM.
    On failure: returns 500, QStash retries. After retries exhausted, goes to DLQ.
    """
    device_id = payload.get("device_id", "unknown")
    logger.info(f"Processing notification for device {device_id}")

    success = await NotificationDispatcher.process_queued(payload)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")

    return {"status": "sent"}
