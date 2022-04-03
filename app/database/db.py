from fastapi_users.db import TortoiseUserDatabase
from tortoise import Tortoise

from app.models.models import UserDB, UserModel


async def get_user_db():
    yield TortoiseUserDatabase(UserDB, UserModel)


Tortoise.init_models(["app.models.models"], "models")
