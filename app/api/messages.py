from beanie import PydanticObjectId

from app.models.models import Message
from app.worker.tasks import send_sms


async def get_messages(limit, skip, user: PydanticObjectId):
    return (
        await Message.find(Message.user == user).limit(int(limit)).skip(skip).to_list()
    )


async def send_message(user: PydanticObjectId, request):
    # Maybe this can be improved with insert_many()
    messages = []
    for data in request:
        d = data.dict()
        messages.append(
            await Message(
                phone=d.get("phone"), message_body=d.get("message_body"), user=user
            ).insert()
        )
    return messages
