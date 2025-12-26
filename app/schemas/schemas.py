from pydantic import BaseModel, constr
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.models import Message, UserModel, Device, ApiKey

# Sobreescribe el dict si no le paso el parámetro name,
# sospecho de que no se están generando los hash
User_Pydantic = pydantic_model_creator(UserModel)

Message_Pydantic_Show = pydantic_model_creator(
    Message, name="MessageShow", exclude=["user"]
)


class Message_Pydantic_Create(BaseModel):
    phone: constr(strip_whitespace=True, regex="(\+?53)?5\d{7}")
    message_body: constr(strip_whitespace=True, min_length=1, max_length=160)


Device_Pydantic = pydantic_model_creator(Device, name="Device")
Device_Pydantic_Create = pydantic_model_creator(Device, name="DeviceCreate", exclude_readonly=True)

ApiKey_Pydantic = pydantic_model_creator(ApiKey, name="ApiKey")
ApiKey_Pydantic_Create = pydantic_model_creator(ApiKey, name="ApiKeyCreate", exclude_readonly=True)
