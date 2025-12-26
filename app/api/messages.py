from uuid import UUID

from app.models.models import Message, Device, ApiKey
from app.schemas.schemas import Message_Pydantic_Show
from app.worker.tasks import send_sms


async def get_messages(user: UUID):
    return await Message_Pydantic_Show.from_queryset(Message.all().filter(user_id=user))


async def send_message(**kwargs):
    user_id = kwargs.get("user_id")
    phone = kwargs.get("phone")
    message_body = kwargs.get("message_body")

    # Seleccionar un dispositivo activo (por ejemplo, el primero)
    device = await Device.get_or_none(is_active=True)
    device_api_key = None
    if device:
        api_key_obj = await ApiKey.get_or_none(device=device, is_active=True)
        if api_key_obj:
            device_api_key = api_key_obj.key

    send_sms.delay(phone, message_body, device_api_key)
    return await Message.create(
        user_id=user_id,
        phone=phone,
        message_body=message_body,
        device=device,
    )
