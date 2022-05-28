from typing import List, Optional

from beanie import Document, Indexed, Link, PydanticObjectId
from fastapi_users.db import BeanieBaseUser


class Message(Document):
    phone: str
    message_body: str
    user: Indexed(PydanticObjectId)

    class Settings:
        name = "Message"


class User(BeanieBaseUser[PydanticObjectId]):
    messages: Optional[List[Link[Message]]]
