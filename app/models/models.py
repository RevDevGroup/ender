from typing import List, Optional

from beanie import Document, PydanticObjectId
from fastapi_users.db import BeanieBaseUser


class Message(Document):
    phone: str
    message_body: str
    user: PydanticObjectId

    class Settings:
        name = "Message"


class User(BeanieBaseUser[PydanticObjectId]):
    messages: Optional[List[Message]] = None
