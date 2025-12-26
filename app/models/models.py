import secrets

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


class Device(Model):
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    api_keys: fields.ReverseRelation["ApiKey"]

    def __str__(self):
        return self.name

class Message(Model):
    phone = fields.CharField(max_length=11)
    message_body = fields.CharField(max_length=160)
    user: fields.ForeignKeyRelation[UserModel] = fields.ForeignKeyField(
        "models.UserModel", related_name="messages"
    )
    device: fields.ForeignKeyRelation[Device] = fields.ForeignKeyField(
        "models.Device", related_name="messages", null=True
    )

    def __str__(self):
        return self.phone


class ApiKey(Model):
    key = fields.CharField(max_length=64, unique=True)
    device: fields.ForeignKeyRelation[Device] = fields.ForeignKeyField(
        "models.Device", related_name="api_keys"
    )
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField(null=True)

    @classmethod
    async def generate_key(cls, device_id: int) -> str:
        key = secrets.token_urlsafe(32)
        await cls.create(key=key, device_id=device_id)
        return key

    def __str__(self):
        return f"ApiKey for {self.device.name}"
