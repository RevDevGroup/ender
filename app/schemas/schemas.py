from typing import List, Optional

from beanie import PydanticObjectId
from fastapi_users import schemas
from pydantic import BaseModel, constr


class Message(BaseModel):
    phone: constr(strip_whitespace=True, regex="(\+?53)?5\d{7}")
    message_body: constr(strip_whitespace=True, min_length=1, max_length=160)


class MessageCreate(Message):
    pass


class MessageRead(Message):
    user: PydanticObjectId


class UserRead(schemas.BaseUser[PydanticObjectId]):
    messages: Optional[List[MessageRead]] = None


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
