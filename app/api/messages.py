from uuid import UUID

from app.models.models import Message
from app.schemas.schemas import Message_Pydantic_Show
from app.worker.tasks import send_sms


async def get_messages(user: UUID):
    return await Message_Pydantic_Show.from_queryset(Message.all().filter(user_id=user))


async def send_message(**kwargs):
    send_sms.delay(kwargs.get("phone"), kwargs.get("message_body"))
    return await Message.create(
        user_id=kwargs.get("user_id"),
        phone=kwargs.get("phone"),
        message_body=kwargs.get("message_body"),
    )
