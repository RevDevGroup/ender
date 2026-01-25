import json
import logging
from collections import defaultdict

import firebase_admin
from fastapi import BackgroundTasks
from firebase_admin import credentials, messaging
from sqlmodel import Session

from app.core.config import settings
from app.models import SMSDevice, SMSMessage

logger = logging.getLogger(__name__)


class FCMService:
    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        if not settings.FIREBASE_SERVICE_ACCOUNT_JSON:
            logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not set. FCM will not work.")
            return

        try:
            service_account_info = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            cls._initialized = True
            logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

    @classmethod
    async def send_sms_notification(cls, device_token: str, payload: dict):
        """
        Sends an FCM data message to the device.
        Payload should contain types like 'task' or 'sms_send'.
        """
        if not cls._initialized:
            cls.initialize()
            if not cls._initialized:
                logger.error("FCM service not initialized. Cannot send notification.")
                return False

        message = messaging.Message(
            data={k: str(v) for k, v in payload.items()},
            token=device_token,
        )

        try:
            response = messaging.send(message)
            logger.info(f"Successfully sent FCM message: {response}")
            return True
        except Exception as e:
            logger.error(f"Error sending FCM message: {e}")
            return False

    @classmethod
    def send_messages_notification(
        cls,
        *,
        session: "Session",
        device: "SMSDevice",
        messages: list["SMSMessage"],
        background_tasks: "BackgroundTasks",
    ):
        """
        Orchestrates sending notifications to a device for a list of messages.
        """

        if not device.fcm_token:
            logger.warning(f"Device {device.id} has no FCM token registered.")
            return

        # Group messages by body to send one notification per unique body
        body_groups: dict[str, list[str]] = defaultdict(list)
        for message in messages:
            body_groups[message.body].append(message.to)

        for body, recipients in body_groups.items():
            payload = {
                "recipients": json.dumps(recipients),
                "body": body,
            }
            background_tasks.add_task(
                cls.send_sms_notification, device.fcm_token, payload
            )

    @classmethod
    def dispatch_notifications(
        cls,
        *,
        session: "Session",
        messages: list["SMSMessage"],
        background_tasks: "BackgroundTasks",
    ):
        """
        Groups messages by device and sends notifications.
        """

        device_messages = defaultdict(list)
        for msg in messages:
            if msg.device_id:
                device_messages[msg.device_id].append(msg)

        for device_id, msgs in device_messages.items():
            device = session.get(SMSDevice, device_id)
            if device:
                cls.send_messages_notification(
                    session=session,
                    device=device,
                    messages=msgs,
                    background_tasks=background_tasks,
                )


# Initialize on module load if config is present
FCMService.initialize()
