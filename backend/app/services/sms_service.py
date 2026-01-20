import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, nulls_last
from sqlmodel import Session, select

from app.core.db import engine
from app.models import SMSDevice, SMSMessage, UserQuota, WebhookConfig
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
        background_tasks: Any,
    ) -> list[SMSMessage]:
        """
        Orchestrates the entire SMS sending process.
        """
        from app import crud
        from app.services.fcm_service import FCMService

        recipient_count = len(message_in.recipients)

        # Check limits
        QuotaService.check_sms_quota(
            session=session, user_id=current_user.id, count=recipient_count
        )

        # Create messages in a transaction
        try:
            messages = crud.create_sms_messages(
                session=session, message_in=message_in, user_id=current_user.id
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Increment counter
        QuotaService.increment_sms_count(
            session=session, user_id=current_user.id, count=recipient_count
        )

        # Determine devices to use
        devices = []
        if message_in.device_id:
            device = session.get(SMSDevice, message_in.device_id)
            if not device or device.status != "online":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified device is not online or found",
                )
            devices = [device]
        else:
            devices = SMSService.get_active_devices(
                session=session, user_id=current_user.id
            )

        if not devices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No online devices available to send SMS",
            )

        # Distribute messages among available devices
        SMSService.distribute_messages(
            session=session, messages=messages, devices=devices
        )

        # Trigger FCM notifications
        FCMService.dispatch_notifications(
            session=session,
            messages=messages,
            background_tasks=background_tasks,
        )

        return messages

    @staticmethod
    def get_active_devices(*, session: Session, user_id: uuid.UUID) -> list[SMSDevice]:
        """Get all online devices for a user"""
        statement = (
            select(SMSDevice)
            .where(SMSDevice.user_id == user_id)
            .where(SMSDevice.status == "online")
            .order_by(nulls_last(desc(SMSDevice.last_heartbeat)))
        )
        return list(session.exec(statement).all())

    @staticmethod
    def assign_message_to_device(
        *, session: Session, message: SMSMessage
    ) -> SMSDevice | None:
        """Assign a single message to an available device"""
        if message.device_id:
            device = session.get(SMSDevice, message.device_id)
            if device and device.status == "online":
                return device

        active_devices = SMSService.get_active_devices(
            session=session, user_id=message.user_id
        )
        if active_devices:
            device = active_devices[0]  # Pick the most recently active
            message.device_id = device.id
            message.status = "assigned"
            session.add(message)
            session.commit()
            return device

        return None

    @staticmethod
    def distribute_messages(
        *, session: Session, messages: list[SMSMessage], devices: list[SMSDevice]
    ) -> None:
        """Assign a list of messages to multiple devices in a round-robin fashion"""
        if not devices:
            return

        for i, message in enumerate(messages):
            device = devices[i % len(devices)]
            message.device_id = device.id
            message.status = "assigned"
            session.add(message)

        session.commit()

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
            to="",
            from_number=from_number,
            body=body,
            status="received",
            message_type="incoming",
            created_at=(
                datetime.fromisoformat(timestamp)
                if timestamp
                else datetime.now(timezone.utc)
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
        session: Session, message_id: str, status: str, error_message: str | None = None
    ) -> dict[str, Any]:
        """
        Process the acknowledgment (ACK) from a device for a sent SMS.
        """
        message = session.get(SMSMessage, uuid.UUID(message_id))
        if not message:
            return {"success": False, "error": "Message not found"}

        message.status = status
        if error_message:
            message.error_message = error_message
        if status == "sent":
            message.sent_at = datetime.now(timezone.utc)

        session.add(message)
        session.commit()
        return {"success": True, "message_id": message_id, "status": status}

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
            message.sent_at = datetime.now(timezone.utc)
        elif status == "delivered":
            message.delivered_at = datetime.now(timezone.utc)

        session.add(message)
        session.commit()

        return {"success": True, "message_id": message_id, "status": status}

    @staticmethod
    async def retry_failed_messages(session: Session) -> dict[str, Any]:
        """Retry failed outgoing messages"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
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
    async def cleanup_offline_devices(session: Session) -> dict[str, Any]:
        """Mark devices as offline if their last heartbeat is too old."""
        five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        statement = (
            select(SMSDevice)
            .where(SMSDevice.status == "online")
            .where(SMSDevice.last_heartbeat < five_minutes_ago)  # type: ignore[operator]
        )
        offline_devices = session.exec(statement).all()

        for device in offline_devices:
            device.status = "offline"
            session.add(device)

        session.commit()
        return {"offline_count": len(offline_devices)}

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
                    quota.last_reset_date = datetime.now(timezone.utc)
                    session.add(quota)
                    reset_count += 1

        session.commit()
        return {"reset_count": reset_count}
