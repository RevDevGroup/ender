import secrets
import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    ItemCreate,
    SMSDevice,
    SMSDeviceCreate,
    SMSDeviceUpdate,
    SMSMessage,
    SMSMessageCreate,
    SMSMessageUpdate,
    User,
    UserCreate,
    UserUpdate,
    WebhookConfig,
    WebhookConfigCreate,
    WebhookConfigUpdate,
)


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


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# SMS CRUD operations
def create_sms_device(
    *, session: Session, device_in: SMSDeviceCreate, user_id: uuid.UUID
) -> SMSDevice:
    """Crear dispositivo SMS con API key generada"""
    api_key = secrets.token_urlsafe(32)
    db_device = SMSDevice.model_validate(
        device_in, update={"user_id": user_id, "api_key": api_key}
    )
    session.add(db_device)
    session.commit()
    session.refresh(db_device)
    return db_device


def get_sms_device(*, session: Session, device_id: uuid.UUID) -> SMSDevice | None:
    """Obtener dispositivo SMS por ID"""
    return session.get(SMSDevice, device_id)


def get_sms_device_by_api_key(*, session: Session, api_key: str) -> SMSDevice | None:
    """Obtener dispositivo SMS por API key"""
    statement = select(SMSDevice).where(SMSDevice.api_key == api_key)
    return session.exec(statement).first()


def get_sms_devices_by_user(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[SMSDevice]:
    """Listar dispositivos SMS de un usuario"""
    statement = (
        select(SMSDevice).where(SMSDevice.user_id == user_id).offset(skip).limit(limit)
    )
    return list(session.exec(statement).all())


def update_sms_device(
    *, session: Session, db_device: SMSDevice, device_in: SMSDeviceUpdate
) -> SMSDevice:
    """Actualizar dispositivo SMS"""
    device_data = device_in.model_dump(exclude_unset=True)
    db_device.sqlmodel_update(device_data)
    session.add(db_device)
    session.commit()
    session.refresh(db_device)
    return db_device


def delete_sms_device(*, session: Session, device_id: uuid.UUID) -> SMSDevice | None:
    """Eliminar dispositivo SMS"""
    device = session.get(SMSDevice, device_id)
    if device:
        session.delete(device)
        session.commit()
    return device


def create_sms_message(
    *, session: Session, message_in: SMSMessageCreate, user_id: uuid.UUID
) -> SMSMessage:
    """Crear mensaje SMS"""
    db_message = SMSMessage.model_validate(message_in, update={"user_id": user_id})
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return db_message


def get_sms_message(*, session: Session, message_id: uuid.UUID) -> SMSMessage | None:
    """Obtener mensaje SMS por ID"""
    return session.get(SMSMessage, message_id)


def get_sms_messages_by_user(
    *,
    session: Session,
    user_id: uuid.UUID,
    message_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SMSMessage]:
    """Listar mensajes SMS de un usuario"""
    statement = select(SMSMessage).where(SMSMessage.user_id == user_id)
    if message_type:
        statement = statement.where(SMSMessage.message_type == message_type)
    statement = (
        statement.order_by(SMSMessage.created_at.desc()).offset(skip).limit(limit)
    )
    return list(session.exec(statement).all())


def update_sms_message(
    *, session: Session, db_message: SMSMessage, message_in: SMSMessageUpdate
) -> SMSMessage:
    """Actualizar mensaje SMS"""
    message_data = message_in.model_dump(exclude_unset=True)
    db_message.sqlmodel_update(message_data)
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return db_message


def create_webhook_config(
    *, session: Session, webhook_in: WebhookConfigCreate, user_id: uuid.UUID
) -> WebhookConfig:
    """Crear configuración de webhook"""
    import json

    # Convertir events a JSON string si es necesario
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
    """Obtener webhook por ID"""
    return session.get(WebhookConfig, webhook_id)


def get_webhook_configs_by_user(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[WebhookConfig]:
    """Listar webhooks de un usuario"""
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
    """Actualizar configuración de webhook"""
    import json

    webhook_data = webhook_in.model_dump(exclude_unset=True)
    # Convertir events a JSON string si es necesario
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
    """Eliminar configuración de webhook"""
    webhook = session.get(WebhookConfig, webhook_id)
    if webhook:
        session.delete(webhook)
        session.commit()
    return webhook
