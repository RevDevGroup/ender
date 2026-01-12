import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import desc, nulls_last
from sqlmodel import Session, select

from app.models import SMSDevice, SMSMessage


class SMSProvider(ABC):
    """Abstract base class for SMS providers"""

    @abstractmethod
    def send_message(self, message: SMSMessage) -> bool:
        """Send SMS"""
        pass


class AndroidSMSProvider(SMSProvider):
    """Provider that assigns messages to Android devices"""

    def __init__(self, session: Session):
        self.session = session

    def send_message(self, message: SMSMessage) -> bool:
        """Assign message to available device"""
        result = self.assign_message_to_device(session=self.session, message=message)
        return result is not None

    @staticmethod
    def assign_message_to_device(
        *, session: Session, message: SMSMessage
    ) -> SMSDevice | None:
        """Assign message to available device"""
        # If you already have a device_id, use that one.
        if message.device_id:
            device = session.get(SMSDevice, message.device_id)
            if device and device.status == "online":
                return device

        # Search for device online by the same user

        statement = (
            select(SMSDevice)
            .where(SMSDevice.user_id == message.user_id)
            .where(SMSDevice.status == "online")
            .order_by(nulls_last(desc(SMSDevice.last_heartbeat)))  # type: ignore[arg-type]
        )
        device = session.exec(statement).first()

        if device:
            message.device_id = device.id
            message.status = "assigned"
            session.add(message)
            session.commit()
            return device

        return None

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
            to="",  # No aplica para mensajes entrantes
            from_number=from_number,
            body=body,
            status="received",
            message_type="incoming",
            created_at=datetime.fromisoformat(timestamp)
            if timestamp
            else datetime.utcnow(),
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        return message
