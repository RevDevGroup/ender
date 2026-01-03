import uuid
from abc import ABC, abstractmethod

from sqlmodel import Session, select

from app.models import SMSDevice, SMSMessage


class SMSProvider(ABC):
    """Clase base abstracta para proveedores SMS"""

    @abstractmethod
    def send_message(self, message: SMSMessage) -> bool:
        """Enviar mensaje SMS"""
        pass


class AndroidSMSProvider(SMSProvider):
    """Proveedor que asigna mensajes a dispositivos Android"""

    def __init__(self, session: Session):
        self.session = session

    def send_message(self, message: SMSMessage) -> bool:
        """Asignar mensaje a dispositivo disponible"""
        result = self.assign_message_to_device(session=self.session, message=message)
        return result is not None

    @staticmethod
    def assign_message_to_device(
        *, session: Session, message: SMSMessage
    ) -> SMSDevice | None:
        """Asignar mensaje a dispositivo disponible"""
        # Si ya tiene device_id, usar ese
        if message.device_id:
            device = session.get(SMSDevice, message.device_id)
            if device and device.status == "online":
                return device

        # Buscar dispositivo online del mismo usuario
        from sqlalchemy import desc, nulls_last

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
        """Procesar SMS entrantes desde Android"""
        from datetime import datetime

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
