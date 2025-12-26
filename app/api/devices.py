from typing import List

from fastapi import APIRouter, Depends, HTTPException
from tortoise.exceptions import DoesNotExist

from app.api.users import current_active_user
from app.models.models import Device, ApiKey, UserDB
from app.schemas.schemas import Device_Pydantic, Device_Pydantic_Create, ApiKey_Pydantic

router = APIRouter(tags=["Devices"], prefix="/devices")


@router.get("", response_model=List[Device_Pydantic])
async def get_devices(user: UserDB = Depends(current_active_user)):
    return await Device_Pydantic.from_queryset(Device.all())


@router.post("", response_model=Device_Pydantic)
async def create_device(
    device: Device_Pydantic_Create, user: UserDB = Depends(current_active_user)
):
    device_obj = await Device.create(**device.dict())
    return await Device_Pydantic.from_tortoise_orm(device_obj)


@router.post("/{device_id}/api-keys", response_model=ApiKey_Pydantic)
async def generate_api_key(
    device_id: int, user: UserDB = Depends(current_active_user)
):
    try:
        device = await Device.get(id=device_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Device not found")

    api_key = await ApiKey.generate_key(device_id)
    return await ApiKey_Pydantic.from_tortoise_orm(await ApiKey.get(key=api_key))


@router.get("/{device_id}/api-keys", response_model=List[ApiKey_Pydantic])
async def get_api_keys(
    device_id: int, user: UserDB = Depends(current_active_user)
):
    try:
        device = await Device.get(id=device_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Device not found")

    return await ApiKey_Pydantic.from_queryset(ApiKey.filter(device=device))