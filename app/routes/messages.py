from typing import List

from fastapi import APIRouter, Depends, status

from app.api.users import current_active_user
from app.models.models import Message, UserDB
from app.schemas.schemas import Message_Pydantic_Create, Message_Pydantic_Show

router = APIRouter(tags=["Messages"], prefix="/messages")


@router.get("/", response_model=List[Message_Pydantic_Show])
async def get_all(user: UserDB = Depends(current_active_user)):
    return await Message_Pydantic_Show.from_queryset(
        Message.all().filter(user_id=user.id)
    )


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_message(
    request: Message_Pydantic_Create, user: UserDB = Depends(current_active_user)
):
    return await Message.create(user_id=user.id, **request.dict())
