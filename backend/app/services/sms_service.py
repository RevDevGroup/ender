import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app import crud
from app.core.db import engine
from app.models import SMSDevice, SMSMessage, UserQuota, WebhookConfig
from app.services.notification_dispatcher import NotificationDispatcher
from app.services.quota_service import QuotaService
from app.services.webhook_service import WebhookService


class SMSProvider(ABC):
    """Abstract base class for SMS providers"""

    @abstractmethod
    def send_message(self, message: SMSMessage) -> bool:
        """Send SMS"""
        pass


class SMSService:
    """Service for handling SMS operations, reporting, and device management"""

    @staticmethod
    async def send_sms(
        *,
        session: Session,
        current_user: Any,
        message_in: Any,
    ) -> list[SMSMessage]:
        """
        Orchestrates the entire SMS sending process.

        Uses the NotificationDispatcher to send notifications via a queue
        for reliable delivery and scalability.
        Recipients are distributed among devices via round robin.
        If no devices are online, messages are queued and will be sent
        when a device comes online.
        """

        recipient_count = len(message_in.recipients)

        # Check limits
        QuotaService.check_sms_quota(
            session=session, user_id=current_user.id, count=recipient_count
        )

        # Determine devices to use
        devices: list[SMSDevice] | None = None
        if message_in.device_id:
            device = session.get(SMSDevice, message_in.device_id)
            if device:
                devices = [device]
        else:
            active_devices = SMSService.get_active_devices(
                session=session, user_id=current_user.id
            )
            if active_devices:
                devices = active_devices

        # Create messages (assigned to devices or queued if no devices online)
        try:
            messages = crud.create_sms_messages(
                session=session,
                message_in=message_in,
                user_id=current_user.id,
                devices=devices,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Increment counter
        QuotaService.increment_sms_count(
            session=session, user_id=current_user.id, count=recipient_count
        )

        # Dispatch notifications only if devices are assigned
        if devices:
            await NotificationDispatcher.dispatch(session=session, messages=messages)

        return messages

    @staticmethod
    def get_active_devices(*, session: Session, user_id: uuid.UUID) -> list[SMSDevice]:
        """Get all devices for a user"""
        statement = select(SMSDevice).where(SMSDevice.user_id == user_id)
        return list(session.exec(statement).all())

    @staticmethod
    def process_incoming_sms(
        *,
        session: Session,
        user_id: uuid.UUID,
        from_number: str,
        body: str,
        timestamp: str | None = None,
    ) -> SMSMessage:
        """Process incoming SMS messages from Android"""
        message = SMSMessage(
            user_id=user_id,
            to="",  # No recipient for incoming
            from_number=from_number,
            body=body,
            status="received",
            message_type="incoming",
            created_at=(
                datetime.fromisoformat(timestamp) if timestamp else datetime.now(UTC)
            ),
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        return message

    @classmethod
    async def handle_incoming_sms(
        cls,
        *,
        session: Session,
        user_id: uuid.UUID,
        from_number: str,
        body: str,
        background_tasks: Any,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Process incoming SMS and trigger webhooks in background"""
        message = cls.process_incoming_sms(
            session=session,
            user_id=user_id,
            from_number=from_number,
            body=body,
            timestamp=timestamp,
        )

        # Retrieve active webhooks for the user
        statement = (
            select(WebhookConfig)
            .where(WebhookConfig.user_id == user_id)
            .where(WebhookConfig.active)
        )
        webhooks = session.exec(statement).all()

        webhook_results = []
        for webhook in webhooks:
            try:
                events = json.loads(webhook.events)
                if "sms_received" in events:
                    # Use background tasks for the actual HTTP call
                    background_tasks.add_task(
                        cls.send_webhook_notification, str(webhook.id), str(message.id)
                    )
                    webhook_results.append({"webhook_id": str(webhook.id)})
            except Exception:
                pass

        return {
            "success": True,
            "message_id": str(message.id),
            "webhooks_sent": len(webhook_results),
        }

    @staticmethod
    async def process_sms_ack(
        session: Session,
        message_id: str,
        ack_status: str,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Process the acknowledgment (ACK) from a device for a sent SMS.
        Each message_id corresponds to a single recipient.
        """
        message = session.get(SMSMessage, uuid.UUID(message_id))
        if not message:
            return {"success": False, "error": "Message not found"}

        message.status = ack_status
        if error_message:
            message.error_message = error_message
        if ack_status == "sent":
            message.sent_at = datetime.now(UTC)
        elif ack_status == "delivered":
            message.delivered_at = datetime.now(UTC)

        session.add(message)
        session.commit()
        return {"success": True, "message_id": message_id, "status": ack_status}

    @staticmethod
    async def send_webhook_notification(
        webhook_id: str, message_id: str
    ) -> dict[str, Any]:
        """Send HTTP notification to configured webhook. Uses fresh session for background tasks."""
        with Session(engine) as session:
            webhook = session.get(WebhookConfig, uuid.UUID(webhook_id))
            if not webhook:
                return {"success": False, "error": "Webhook not found"}

            message = session.get(SMSMessage, uuid.UUID(message_id))
            if not message:
                return {"success": False, "error": "Message not found"}

            result = await WebhookService.send_webhook(webhook, message)
            if result.get("success"):
                message.webhook_sent = True
                session.add(message)
                session.commit()

            return result

    @staticmethod
    async def update_message_status(
        session: Session, message_id: str, status: str, error_message: str | None = None
    ) -> dict[str, Any]:
        """Update message status"""
        message = session.get(SMSMessage, uuid.UUID(message_id))
        if not message:
            return {"success": False, "error": "Message not found"}

        message.status = status
        if error_message:
            message.error_message = error_message

        if status == "sent":
            message.sent_at = datetime.now(UTC)
        elif status == "delivered":
            message.delivered_at = datetime.now(UTC)

        session.add(message)
        session.commit()

        return {"success": True, "message_id": message_id, "status": status}

    @staticmethod
    async def retry_failed_messages(session: Session) -> dict[str, Any]:
        """Retry failed outgoing messages"""
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        statement = (
            select(SMSMessage)
            .where(SMSMessage.status == "failed")
            .where(SMSMessage.created_at >= cutoff)
            .where(SMSMessage.message_type == "outgoing")
            .limit(50)
        )
        messages = session.exec(statement).all()

        retried_count = 0
        for message in messages:
            message.status = "pending"
            session.add(message)
            retried_count += 1

        session.commit()
        return {"retried": retried_count}

    @staticmethod
    async def reset_monthly_quotas(session: Session) -> dict[str, Any]:
        """Reset monthly SMS counters"""
        statement = select(UserQuota)
        quotas = session.exec(statement).all()

        reset_count = 0
        for quota in quotas:
            if quota.last_reset_date:
                if quota.last_reset_date.day == 1:  # Day 1 of the month
                    quota.sms_sent_this_month = 0
                    quota.last_reset_date = datetime.now(UTC)
                    session.add(quota)
                    reset_count += 1

        session.commit()
        return {"reset_count": reset_count}
