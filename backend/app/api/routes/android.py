import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app import crud
from app.api.deps import get_device_by_api_key
from app.core.db import engine
from app.models import SMSDevice, SMSMessage
from app.services.websocket_manager import websocket_manager
from app.tasks.sms_tasks import process_incoming_sms, update_message_status

router = APIRouter(prefix="/android", tags=["android"])


async def _send_pending_messages(
    session: Session, device: SMSDevice, websocket: WebSocket
) -> None:
    """Send pending assigned messages to the device"""
    statement = (
        select(SMSMessage)
        .where(SMSMessage.device_id == device.id)
        .where(SMSMessage.status == "assigned")
        .where(SMSMessage.message_type == "outgoing")
        .order_by(SMSMessage.created_at)
        .limit(50)
    )
    messages = session.exec(statement).all()

    # Refresh device. I need to find a better way to manage the Session
    session.refresh(device)

    for message in messages:
        message_data = {
            "type": "task",
            "message_id": str(message.id),
            "to": message.to,
            "body": message.body,
        }
        await websocket.send_json(message_data)
        # Update to sending status
        message.status = "sending"
        session.add(message)

    session.commit()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: str = Query(...),
):
    """Persistent WebSocket connection for Android devices"""
    with Session(engine) as session:
        # API Key validation
        device = get_device_by_api_key(session=session, api_key=api_key)

        await websocket_manager.connect_device(websocket, device.id)

        # Update device status
        device.status = "online"
        device.last_heartbeat = datetime.now(timezone.utc)
        session.add(device)
        session.commit()

        try:
            # Send pending message on connection
            await _send_pending_messages(session, device, websocket)

            while True:
                # Receive client messages
                data = await websocket.receive_json()

                message_type = data.get("type")

                if message_type == "register":
                    # Update device info
                    device.name = data.get("device_name", device.name)
                    device.phone_number = data.get("phone_number", device.phone_number)
                    device.last_heartbeat = datetime.now(timezone.utc)
                    session.add(device)
                    session.commit()

                    await websocket.send_json(
                        {
                            "type": "registered",
                            "device_id": str(device.id),
                            "status": "ok",
                        }
                    )

                elif message_type == "sms_report":
                    # SMS status delivery
                    raw_id = data.get("message_id")
                    try:
                        message_id = uuid.UUID(raw_id)
                    except (TypeError, ValueError):
                        await websocket.send_json(
                            {"type": "error", "message": "Invalid message_id"}
                        )
                        continue
                    status_value = data.get("status")  # sent, failed
                    error = data.get("error")

                    message = crud.get_sms_message(
                        session=session, message_id=message_id
                    )
                    if message and message.device_id == device.id:
                        update_message_status.delay(
                            str(message_id), status_value, error
                        )

                    await websocket.send_json(
                        {"type": "ack", "message_id": data.get("message_id")}
                    )

                elif message_type == "sms_incoming":
                    # Report sms incoming
                    from_number = data.get("from")
                    body = data.get("body")
                    timestamp = data.get("timestamp")

                    process_incoming_sms.delay(
                        str(device.user_id), from_number, body, timestamp
                    )

                    await websocket.send_json({"type": "ack", "status": "received"})

                elif message_type == "ping":
                    # Heartbeat/keepalive
                    device.last_heartbeat = datetime.now(timezone.utc)
                    session.add(device)
                    session.commit()

                    # Send pending messages with the ping
                    await _send_pending_messages(session, device, websocket)

                    await websocket.send_json({"type": "pong"})

                else:
                    await websocket.send_json(
                        {"type": "error", "message": f"Unknown message: {message_type}"}
                    )

        except WebSocketDisconnect:
            # Disconnect Device
            await websocket_manager.disconnect_device(device.id)
            device.status = "offline"
            session.add(device)
            session.commit()
        except Exception:
            await websocket_manager.disconnect_device(device.id)
            device.status = "offline"
            session.add(device)
            session.commit()
            raise
