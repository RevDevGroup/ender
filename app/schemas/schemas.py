from typing import List, Optional

from beanie import PydanticObjectId
from fastapi_users import schemas
from pydantic import BaseModel, Field, constr


class Message(BaseModel):
    phone: constr(strip_whitespace=True, regex="(\+?53)?5\d{7}")
    message_body: constr(strip_whitespace=True, min_length=1, max_length=160)

    class Config:
        orm_mode = True


class MessageCreate(Message):
    pass


class MessageRead(Message):
    id: PydanticObjectId = Field(..., alias="_id", title="Message ID")
    user: PydanticObjectId


class UserRead(schemas.BaseUser[PydanticObjectId]):
    messages: Optional[List[MessageRead]]


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
