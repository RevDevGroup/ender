from beanie import PydanticObjectId

from app.models.models import Message
from app.worker.tasks import send_sms


async def get_messages(user: PydanticObjectId):
    return await Message.find(Message.user == user).to_list()


async def send_message(user: PydanticObjectId, **kwargs):
    # await send_sms.delay(kwargs.get("phone"), kwargs.get("message_body"))
    return await Message(
        phone=kwargs.get("phone"), message_body=kwargs.get("message_body"), user=user
    ).insert()


async def send_messages():
    pass
    # return await Message()
