from typing import List

from fastapi import APIRouter, Depends, status

from app.api.messages import get_messages, send_message
from app.api.users import current_active_user
from app.models.models import UserDB
from app.schemas.schemas import Message_Pydantic_Create, Message_Pydantic_Show

router = APIRouter(tags=["Messages"], prefix="/messages")


@router.get("", response_model=List[Message_Pydantic_Show])
async def get_all(user: UserDB = Depends(current_active_user)):
    return await get_messages(user=user.id)


@router.post(
    "/create", status_code=status.HTTP_200_OK, response_model=Message_Pydantic_Show
)
async def create_message(
    request: Message_Pydantic_Create, user: UserDB = Depends(current_active_user)
):
    return await send_message(user_id=user.id, **request.dict())
