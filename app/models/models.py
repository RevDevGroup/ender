from fastapi_users import models
from fastapi_users.db import TortoiseBaseUserModel
from tortoise import fields
from tortoise.contrib.pydantic import PydanticModel
from tortoise.models import Model


class User(models.BaseUser):
    pass


class UserCreate(models.BaseUserCreate):
    pass


class UserUpdate(models.BaseUserUpdate):
    pass


class UserModel(TortoiseBaseUserModel):
    messages: fields.ReverseRelation["Message"]

    class PydanticMeta:
        exclude = ("hashed_password",)


class UserDB(User, models.BaseUserDB, PydanticModel):
    class Config:
        orm_mode = True
        orig_model = UserModel


class Message(Model):
    phone = fields.CharField(max_length=8)
    message_body = fields.CharField(max_length=160)
    user: fields.ForeignKeyRelation[UserModel] = fields.ForeignKeyField(
        "models.UserModel", related_name="messages"
    )

    def __str__(self):
        return self.phone
