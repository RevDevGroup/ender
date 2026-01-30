import json
import logging

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

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
        Payload should contain: message_id, recipients (JSON string), body
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
