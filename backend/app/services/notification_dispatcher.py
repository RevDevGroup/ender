"""
Notification Dispatcher - Decoupled notification delivery system.

This module provides an abstraction layer for dispatching notifications
to different types of devices (Android/FCM, modems, etc.) using a
queue-based approach for reliability and scalability.
"""

import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.models import SMSDevice, SMSMessage
from app.services.qstash_service import QStashService

logger = logging.getLogger(__name__)


class DeviceType(str, Enum):
    """Supported device types for SMS delivery."""

    ANDROID = "android"  # Uses FCM
    MODEM = "modem"  # Future: USB/Serial modems
    # Add more device types here as needed


class NotificationPayload:
    """Standardized payload for device notifications."""

    def __init__(
        self,
        device_id: UUID,
        device_token: str,
        device_type: DeviceType,
        messages: list[dict],  # [{message_id, recipient}]
        body: str,
    ):
        self.device_id = device_id
        self.device_token = device_token
        self.device_type = device_type
        self.messages = messages
        self.body = body

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": str(self.device_id),
            "device_token": self.device_token,
            "device_type": self.device_type.value,
            "messages": self.messages,
            "body": self.body,
        }


class BaseDeviceHandler(ABC):
    """Abstract base class for device-specific notification handlers."""

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """Return the device type this handler supports."""
        pass

    @abstractmethod
    async def send(self, device_token: str, payload: dict[str, Any]) -> bool:
        """
        Send notification to the device.

        Args:
            device_token: Device-specific token/identifier
            payload: Notification payload

        Returns:
            True if sent successfully, False otherwise
        """
        pass


class FCMHandler(BaseDeviceHandler):
    """Handler for Android devices via Firebase Cloud Messaging."""

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.ANDROID

    async def send(self, device_token: str, payload: dict[str, Any]) -> bool:
        from app.services.fcm_service import FCMService

        # Send messages as JSON array with {message_id, recipient} pairs
        fcm_payload = {
            "messages": json.dumps(payload["messages"]),
            "body": payload["body"],
        }
        return await FCMService.send_sms_notification(device_token, fcm_payload)


class ModemHandler(BaseDeviceHandler):
    """Handler for USB/Serial modems (placeholder for future implementation)."""

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.MODEM

    async def send(self, device_token: str, payload: dict[str, Any]) -> bool:
        # TODO: Implement modem communication
        logger.warning("Modem handler not yet implemented")
        return False


class NotificationDispatcher:
    """
    Central dispatcher for routing notifications to appropriate handlers.

    Always uses QStash for reliable async delivery.
    In local development, run the QStash CLI dev server:
        npx @upstash/qstash-cli dev

    See: https://upstash.com/docs/qstash/howto/local-development
    """

    _handlers: dict[DeviceType, BaseDeviceHandler] = {}

    @classmethod
    def register_handler(cls, handler: BaseDeviceHandler) -> None:
        """Register a device handler."""
        cls._handlers[handler.device_type] = handler
        logger.info(f"Registered handler for {handler.device_type.value}")

    @classmethod
    def get_handler(cls, device_type: DeviceType) -> BaseDeviceHandler | None:
        """Get handler for a device type."""
        return cls._handlers.get(device_type)

    @classmethod
    def initialize(cls) -> None:
        """Initialize default handlers."""
        cls.register_handler(FCMHandler())
        cls.register_handler(ModemHandler())
        logger.info("Notification dispatcher initialized")

    @classmethod
    def _get_device_type(cls, device: "SMSDevice") -> DeviceType:
        """
        Determine device type from device model.

        Currently defaults to ANDROID. In the future, this could be
        based on a device.type field or other criteria.
        """
        # TODO: Add device.type field to SMSDevice model for explicit typing
        # For now, assume all devices with fcm_token are Android
        if device.fcm_token:
            return DeviceType.ANDROID
        return DeviceType.MODEM

    @classmethod
    async def dispatch(
        cls,
        session: "Session",
        messages: list["SMSMessage"],
    ) -> None:
        """
        Dispatch notifications for a list of messages.

        Messages are grouped by device, and one notification is sent per device
        containing all recipients for that device.

        Args:
            session: Database session
            messages: List of SMSMessage to dispatch
        """
        from app.models import SMSDevice

        if not messages:
            return

        # Group messages by device_id
        by_device: dict[UUID, list[SMSMessage]] = defaultdict(list)
        for msg in messages:
            if msg.device_id:
                by_device[msg.device_id].append(msg)

        # Get the body (same for all messages in a batch)
        body = messages[0].body

        # Dispatch one notification per device
        for device_id, device_messages in by_device.items():
            device = session.get(SMSDevice, device_id)
            if not device:
                logger.warning(f"Device {device_id} not found")
                continue

            device_type = cls._get_device_type(device)
            device_token = device.fcm_token

            if not device_token:
                logger.warning(f"Device {device_id} has no token")
                continue

            # Build messages array with {message_id, recipient} pairs
            messages_data = [
                {"message_id": str(msg.id), "recipient": msg.to}
                for msg in device_messages
            ]

            payload = NotificationPayload(
                device_id=device_id,
                device_token=device_token,
                device_type=device_type,
                messages=messages_data,
                body=body,
            )

            await cls._dispatch_single(payload)

    @classmethod
    async def _dispatch_single(cls, payload: NotificationPayload) -> None:
        """
        Dispatch a single notification payload via QStash.

        QStash is always required. In local development, run:
            npx @upstash/qstash-cli dev
        """
        if not QStashService.is_available():
            logger.error(
                "QStash not available - cannot dispatch notification. "
                "In local dev, run: npx @upstash/qstash-cli dev"
            )
            return

        QStashService.enqueue(
            endpoint="/api/v1/internal/notifications/send",
            payload=payload.to_dict(),
            deduplication_id=f"{payload.device_id}-{hash(payload.body)}-{len(payload.messages)}",
        )

    @classmethod
    async def process_queued(cls, payload_dict: dict[str, Any]) -> bool:
        """
        Process a queued notification (called by webhook).

        Args:
            payload_dict: Deserialized notification payload

        Returns:
            True if processed successfully
        """
        device_type = DeviceType(payload_dict["device_type"])
        handler = cls.get_handler(device_type)

        if not handler:
            logger.error(f"No handler for device type: {device_type}")
            return False

        return await handler.send(
            payload_dict["device_token"],
            {
                "messages": payload_dict["messages"],
                "body": payload_dict["body"],
            },
        )
