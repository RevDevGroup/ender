from typing import List

from fastapi import APIRouter, Depends, Query, status

from app.api.messages import get_messages, send_message
from app.api.users import current_active_user
from app.schemas.schemas import MessageCreate, MessageRead, UserRead

router = APIRouter(tags=["Messages"], prefix="/messages")


@router.get("", response_model=List[MessageRead])
async def get_all(
    limit: str = Query(
        default=10,
        min_length=1,
        max_length=3,
        regex="^[1-9][0-9]?$|^100$",
        description="Limit the number of results from 1 - 100",
    ),
    user: UserRead = Depends(current_active_user),
):
    return await get_messages(user=user.id)


@router.post("/create", status_code=status.HTTP_200_OK, response_model=MessageRead)
async def create_message(
    request: MessageCreate, user: UserRead = Depends(current_active_user)
):
    return await send_message(user=user.id, **request.dict())
