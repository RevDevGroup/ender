import motor.motor_asyncio
from fastapi_users.db import BeanieUserDatabase

from app.core.config import DATABASE_URL, DB_NAME
from app.models.models import User

client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL, uuidRepresentation="standard"
)

db = client[DB_NAME]


async def get_user_db():
    yield BeanieUserDatabase(User)
