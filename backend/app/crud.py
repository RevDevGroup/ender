import secrets
import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    SMSDevice,
    SMSDeviceCreate,
    SMSDeviceUpdate,
    SMSMessage,
    SMSMessageCreate,
    SMSMessageUpdate,
    SMSOutbox,
    User,
    UserCreate,
    UserUpdate,
    WebhookConfig,
    WebhookConfigCreate,
    WebhookConfigUpdate,
)
from app.utils import validate_sms_device


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


# SMS CRUD operations
def create_sms_device(
    *, session: Session, device_in: SMSDeviceCreate, user_id: uuid.UUID
) -> SMSDevice:
    """Create SMS device with generated API key"""
    api_key = secrets.token_urlsafe(32)
    db_device = SMSDevice.model_validate(
        device_in, update={"user_id": user_id, "api_key": api_key}
    )
    session.add(db_device)
    session.commit()
    session.refresh(db_device)
    return db_device


def get_sms_device(*, session: Session, device_id: uuid.UUID) -> SMSDevice | None:
    """Get SMS device by ID"""
    return session.get(SMSDevice, device_id)


def get_sms_device_by_api_key(*, session: Session, api_key: str) -> SMSDevice | None:
    """Get SMS device by API key"""
    statement = select(SMSDevice).where(SMSDevice.api_key == api_key)
    return session.exec(statement).first()


def get_sms_devices_by_user(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[SMSDevice]:
    """List SMS devices for a user"""
    statement = (
        select(SMSDevice).where(SMSDevice.user_id == user_id).offset(skip).limit(limit)
    )
    return list(session.exec(statement).all())


def update_sms_device(
    *, session: Session, db_device: SMSDevice, device_in: SMSDeviceUpdate
) -> SMSDevice:
    """Update SMS device"""
    device_data = device_in.model_dump(exclude_unset=True)
    db_device.sqlmodel_update(device_data)
    session.add(db_device)
    session.commit()
    session.refresh(db_device)
    return db_device


def delete_sms_device(*, session: Session, device_id: uuid.UUID) -> SMSDevice | None:
    """Delete SMS device"""
    device = session.get(SMSDevice, device_id)
    if device:
        session.delete(device)
        session.commit()
    return device


def create_sms_outbox_message(
    *, session: Session, message_in: SMSMessageCreate, user_id: uuid.UUID
) -> SMSMessage:
    """
    Create an SMS message and its corresponding outbox entry in a single transaction.
    """
    validate_sms_device(
        session=session, device_id=message_in.device_id, user_id=user_id
    )

    db_message = SMSMessage.model_validate(message_in, update={"user_id": user_id})
    session.add(db_message)

    outbox_payload = {
        "type": "task",
        "message_id": str(db_message.id),
        "to": db_message.to,
        "body": db_message.body,
    }
    db_outbox = SMSOutbox(
        sms_message=db_message,
        device_id=db_message.device_id,
        payload=outbox_payload,
        status="pending",
    )
    session.add(db_outbox)

    session.commit()

    session.refresh(db_message)
    session.refresh(db_outbox)

    outbox_payload["message_id"] = str(db_message.id)
    outbox_payload["outbox_id"] = str(db_outbox.id)
    db_outbox.payload = outbox_payload
    session.add(db_outbox)
    session.commit()
    session.refresh(db_outbox)

    return db_message


def get_sms_message(*, session: Session, message_id: uuid.UUID) -> SMSMessage | None:
    """Get SMS message by ID"""
    return session.get(SMSMessage, message_id)


def get_sms_messages_by_user(
    *,
    session: Session,
    user_id: uuid.UUID,
    message_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SMSMessage]:
    """List SMS messages for a user"""
    statement = select(SMSMessage).where(SMSMessage.user_id == user_id)
    if message_type:
        statement = statement.where(SMSMessage.message_type == message_type)
    from sqlalchemy import desc as sa_desc

    statement = (
        statement.order_by(sa_desc(SMSMessage.created_at)).offset(skip).limit(limit)  # type: ignore[arg-type]
    )
    return list(session.exec(statement).all())


def update_sms_message(
    *, session: Session, db_message: SMSMessage, message_in: SMSMessageUpdate
) -> SMSMessage:
    """Update SMS message"""
    message_data = message_in.model_dump(exclude_unset=True)
    db_message.sqlmodel_update(message_data)
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return db_message


def create_webhook_config(
    *, session: Session, webhook_in: WebhookConfigCreate, user_id: uuid.UUID
) -> WebhookConfig:
    """Create webhook configuration"""
    import json

    if isinstance(webhook_in.events, list):
        webhook_in.events = json.dumps(webhook_in.events)

    db_webhook = WebhookConfig.model_validate(webhook_in, update={"user_id": user_id})
    session.add(db_webhook)
    session.commit()
    session.refresh(db_webhook)
    return db_webhook


def get_webhook_config(
    *, session: Session, webhook_id: uuid.UUID
) -> WebhookConfig | None:
    """Get webhook by ID"""
    return session.get(WebhookConfig, webhook_id)


def get_webhook_configs_by_user(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[WebhookConfig]:
    """List webhooks for a user"""
    statement = (
        select(WebhookConfig)
        .where(WebhookConfig.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def update_webhook_config(
    *,
    session: Session,
    db_webhook: WebhookConfig,
    webhook_in: WebhookConfigUpdate,
) -> WebhookConfig:
    """Update webhook configuration"""
    import json

    webhook_data = webhook_in.model_dump(exclude_unset=True)
    if "events" in webhook_data and isinstance(webhook_data["events"], list):
        webhook_data["events"] = json.dumps(webhook_data["events"])

    db_webhook.sqlmodel_update(webhook_data)
    session.add(db_webhook)
    session.commit()
    session.refresh(db_webhook)
    return db_webhook


def delete_webhook_config(
    *, session: Session, webhook_id: uuid.UUID
) -> WebhookConfig | None:
    """Delete webhook configuration"""
    webhook = session.get(WebhookConfig, webhook_id)
    if webhook:
        session.delete(webhook)
        session.commit()
    return webhook
