from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.models import Message, UserModel

# Sobreescribe el dict si no le paso el parámetro name,
# sospecho de que no se están generando los hash
User_Pydantic = pydantic_model_creator(UserModel)
Message_Pydantic_Create = pydantic_model_creator(
    Message, name="MessageCreate", exclude=["id", "user", "user_id"]
)
Message_Pydantic_Show = pydantic_model_creator(
    Message, name="MessageShow", exclude=["user"]
)
