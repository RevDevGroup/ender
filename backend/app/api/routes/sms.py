import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app import crud
from app.api.deps import (
    CurrentDevice,
    CurrentUser,
    CurrentUserOrIntegration,
    SessionDep,
)
from app.models import (
    FCMTokenUpdate,
    Message,
    SMSDeviceCreate,
    SMSDeviceCreatePublic,
    SMSDevicePublic,
    SMSDevicesPublic,
    SMSDeviceUpdate,
    SMSIncoming,
    SMSMessageCreate,
    SMSMessagePublic,
    SMSMessageSendPublic,
    SMSMessagesPublic,
    SMSReport,
)
from app.services.quota_service import QuotaService
from app.services.sms_service import SMSService

router = APIRouter(prefix="/sms", tags=["sms"])


# SMS Sending and Management
@router.post(
    "/send", status_code=status.HTTP_201_CREATED, response_model=SMSMessageSendPublic
)
async def send_sms(
    *,
    session: SessionDep,
    current_user: CurrentUserOrIntegration,
    message_in: SMSMessageCreate,
) -> SMSMessageSendPublic:
    """Send SMS (Single or Bulk). Messages are queued if no devices are online."""
    messages = await SMSService.send_sms(
        session=session,
        current_user=current_user,
        message_in=message_in,
    )

    # Check if messages were queued (no device assigned) or processing
    is_queued = messages and messages[0].status == "queued"

    return SMSMessageSendPublic(
        batch_id=messages[0].batch_id if messages else None,
        message_ids=[m.id for m in messages],
        recipients_count=len(messages),
        status="queued" if is_queued else "processing",
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


# Device Callback Endpoints
@router.post("/report", response_model=Message)
async def report_sms_status(
    *,
    session: SessionDep,
    _device: CurrentDevice,
    report: SMSReport,
) -> Message:
    """Callback for Android device to report SMS sending status (ACK)"""
    result = await SMSService.process_sms_ack(
        session=session,
        message_id=str(report.message_id),
        ack_status=report.status,
        error_message=report.error_message,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return Message(message="Status updated")


@router.post("/incoming", response_model=Message)
async def report_incoming_sms(
    *,
    session: SessionDep,
    device: CurrentDevice,
    incoming: SMSIncoming,
    background_tasks: BackgroundTasks,
) -> Message:
    """Callback for Android device to report received SMS"""
    await SMSService.handle_incoming_sms(
        session=session,
        user_id=device.user_id,
        from_number=incoming.from_number,
        body=incoming.body,
        background_tasks=background_tasks,
        timestamp=incoming.timestamp,
    )
    return Message(message="Incoming SMS registered")


@router.post("/fcm-token", response_model=Message)
def update_fcm_token(
    *,
    session: SessionDep,
    device: CurrentDevice,
    token_in: FCMTokenUpdate,
) -> Message:
    """Update device FCM token using API Key"""
    device.fcm_token = token_in.fcm_token
    session.add(device)
    session.commit()
    return Message(message="FCM token updated")
