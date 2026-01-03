import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.api.deps import get_device_by_api_key
from app.core.db import engine
from app.models import SMSDevice
from app.services.websocket_manager import websocket_manager
from app.tasks.sms_tasks import process_incoming_sms, process_sms_ack

router = APIRouter(prefix="/android", tags=["android"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: str = Query(...),
) -> None:
    """Persistent WebSocket connection for Android devices."""
    with Session(engine) as session:
        device = get_device_by_api_key(session=session, api_key=api_key)
        logging.info("Device attempting to connect via WebSocket:", device)
        if not device:
            await websocket.close(code=4001, reason="Invalid API Key")
            return

    # Connect device and start Redis listener
    listener_task = await websocket_manager.connect(websocket, device.id)

    # Update device status in DB (last heartbeat)
    _update_device_heartbeat_in_db(device.id)

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "register":
                _update_device_info_in_db(device.id, data)
                await websocket.send_json(
                    {
                        "type": "registered",
                        "device_id": str(device.id),
                        "status": "ok",
                    }
                )

            elif message_type == "sms_report":
                raw_outbox_id = data.get("outbox_id")
                try:
                    outbox_id = uuid.UUID(raw_outbox_id)
                except (TypeError, ValueError):
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid outbox_id"}
                    )
                    continue

                status_value = data.get("status")  # sent, failed
                error = data.get("error")
                process_sms_ack.delay(str(outbox_id), status_value, error)
                await websocket.send_json({"type": "ack", "outbox_id": raw_outbox_id})

            elif message_type == "sms_incoming":
                process_incoming_sms.delay(
                    str(device.user_id),
                    data.get("from"),
                    data.get("body"),
                    data.get("timestamp"),
                )
                await websocket.send_json({"type": "ack", "status": "received"})

            elif message_type == "ping":
                await websocket_manager.refresh_heartbeat(device.id)
                _update_device_heartbeat_in_db(device.id)
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

    except WebSocketDisconnect:
        pass  # Normal disconnect
    except Exception:
        # Log exception here if needed
        pass
    finally:
        # Cleanup
        listener_task.cancel()
        await websocket_manager.disconnect(device.id)
        _update_device_status_in_db(device.id, "offline")


# Helper functions to interact with DB in a new session
def _update_device_heartbeat_in_db(device_id: uuid.UUID) -> None:
    with Session(engine) as session:
        device = session.get(SMSDevice, device_id)
        if device:
            device.last_heartbeat = datetime.now(timezone.utc)
            device.status = "online"
            session.add(device)
            session.commit()


def _update_device_info_in_db(device_id: uuid.UUID, data: dict[str, Any]) -> None:
    with Session(engine) as session:
        device = session.get(SMSDevice, device_id)
        if device:
            device.name = data.get("device_name", device.name)
            device.phone_number = data.get("phone_number", device.phone_number)
            device.last_heartbeat = datetime.now(timezone.utc)
            session.add(device)
            session.commit()


def _update_device_status_in_db(device_id: uuid.UUID, status: str) -> None:
    with Session(engine) as session:
        device = session.get(SMSDevice, device_id)
        if device:
            device.status = status
            session.add(device)
            session.commit()
