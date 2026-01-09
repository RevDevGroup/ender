import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    SMSBulkCreate,
    SMSBulkSendPublic,
    SMSDeviceCreate,
    SMSDeviceCreatePublic,
    SMSDevicePublic,
    SMSDevicesPublic,
    SMSDeviceUpdate,
    SMSMessageCreate,
    SMSMessagePublic,
    SMSMessageSendPublic,
    SMSMessagesPublic,
)
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/sms", tags=["sms"])


# SMS Sending and Management
@router.post(
    "/send", status_code=status.HTTP_201_CREATED, response_model=SMSMessageSendPublic
)
def send_sms(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    message_in: SMSMessageCreate,
) -> SMSMessageSendPublic:
    """Send SMS"""
    # Check limits
    QuotaService.check_sms_quota(session=session, user_id=current_user.id, count=1)

    # Create message and outbox entry in a transaction
    try:
        message = crud.create_sms_outbox_message(
            session=session, message_in=message_in, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Increment counter
    QuotaService.increment_sms_count(session=session, user_id=current_user.id, count=1)

    return SMSMessageSendPublic(message_id=message.id, status=message.status)


@router.post(
    "/send-bulk", status_code=status.HTTP_201_CREATED, response_model=SMSBulkSendPublic
)
def send_bulk_sms(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    bulk_in: SMSBulkCreate,
) -> SMSBulkSendPublic:
    """Send SMS to multiple recipients"""
    # Check limits
    QuotaService.check_sms_quota(
        session=session, user_id=current_user.id, count=len(bulk_in.recipients)
    )

    # Create messages and outbox entries
    message_ids = []
    for recipient in bulk_in.recipients:
        message_in = SMSMessageCreate(
            to=recipient, body=bulk_in.body, device_id=bulk_in.device_id
        )
        try:
            message = crud.create_sms_outbox_message(
                session=session, message_in=message_in, user_id=current_user.id
            )
            message_ids.append(message.id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Increment counter
    QuotaService.increment_sms_count(
        session=session, user_id=current_user.id, count=len(bulk_in.recipients)
    )

    return SMSBulkSendPublic(
        total_recipients=len(bulk_in.recipients),
        status="processing",
        message_ids=message_ids,
    )


@router.get("/messages", response_model=SMSMessagesPublic)
def list_messages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    message_type: str | None = Query(None),
) -> SMSMessagesPublic:
    """List messages"""
    messages = crud.get_sms_messages_by_user(
        session=session,
        user_id=current_user.id,
        message_type=message_type,
        skip=skip,
        limit=limit,
    )
    return SMSMessagesPublic(
        data=[SMSMessagePublic.model_validate(m) for m in messages], count=len(messages)
    )


@router.get("/messages/{message_id}", response_model=SMSMessagePublic)
def get_message(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    message_id: uuid.UUID,
) -> SMSMessagePublic:
    """Get specific message"""
    message = crud.get_sms_message(session=session, message_id=message_id)
    if not message or message.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )
    return SMSMessagePublic.model_validate(message)


@router.get("/incoming", response_model=SMSMessagesPublic)
def list_incoming_messages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> SMSMessagesPublic:
    """List incoming SMS"""
    messages = crud.get_sms_messages_by_user(
        session=session,
        user_id=current_user.id,
        message_type="incoming",
        skip=skip,
        limit=limit,
    )
    return SMSMessagesPublic(
        data=[SMSMessagePublic.model_validate(m) for m in messages], count=len(messages)
    )


# Device management
@router.post(
    "/devices",
    status_code=status.HTTP_201_CREATED,
    response_model=SMSDeviceCreatePublic,
)
def create_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_in: SMSDeviceCreate,
) -> SMSDeviceCreatePublic:
    """Register new device"""
    # Validate device limit
    QuotaService.check_device_quota(session=session, user_id=current_user.id)

    # Create device
    device = crud.create_sms_device(
        session=session, device_in=device_in, user_id=current_user.id
    )

    # Increment device count
    QuotaService.increment_device_count(session=session, user_id=current_user.id)

    return SMSDeviceCreatePublic(
        device_id=device.id,
        api_key=device.api_key,
        status=device.status,
    )


@router.get("/devices", response_model=SMSDevicesPublic)
def list_devices(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> SMSDevicesPublic:
    """Get devices"""
    devices = crud.get_sms_devices_by_user(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return SMSDevicesPublic(
        data=[SMSDevicePublic.model_validate(d) for d in devices], count=len(devices)
    )


@router.get("/devices/{device_id}", response_model=SMSDevicePublic)
def get_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_id: uuid.UUID,
) -> SMSDevicePublic:
    """Get device"""
    device = crud.get_sms_device(session=session, device_id=device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    return SMSDevicePublic.model_validate(device)


@router.put("/devices/{device_id}", response_model=SMSDevicePublic)
def update_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_id: uuid.UUID,
    device_in: SMSDeviceUpdate,
) -> SMSDevicePublic:
    """Update device"""
    device = crud.get_sms_device(session=session, device_id=device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    device = crud.update_sms_device(
        session=session, db_device=device, device_in=device_in
    )
    return SMSDevicePublic.model_validate(device)


@router.delete("/devices/{device_id}", response_model=Message)
def delete_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_id: uuid.UUID,
) -> Message:
    """Delete device"""
    device = crud.get_sms_device(session=session, device_id=device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    crud.delete_sms_device(session=session, device_id=device_id)
    # Decrement counter
    QuotaService.decrement_device_count(session=session, user_id=current_user.id)
    return Message(message="Device deleted")
