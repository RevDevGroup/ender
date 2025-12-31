import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.core.celery_app import celery_app
from app.core.db import engine
from app.models import SMSDevice, SMSMessage, SMSOutbox, UserQuota, WebhookConfig
from app.services.sms_service import AndroidSMSProvider
from app.services.webhook_service import WebhookService
from app.services.websocket_manager import websocket_manager


@celery_app.task
def dispatch_outbox_messages() -> dict:
    """
    Scans for pending messages in the SMSOutbox and sends them via WebSocket
    if the target device is connected.
    """
    processed_count = 0
    sent_count = 0
    with Session(engine) as session:
        # Get pending messages from the outbox
        statement = (
            select(SMSOutbox)
            .where(SMSOutbox.status == "pending")
            .order_by(SMSOutbox.created_at)
            .limit(100)
        )
        pending_messages = session.exec(statement).all()
        processed_count = len(pending_messages)

        for outbox_item in pending_messages:
            if outbox_item.device_id and asyncio.run(
                websocket_manager.is_connected(outbox_item.device_id)
            ):
                # Mark as sending
                outbox_item.status = "sending"
                outbox_item.sending_at = datetime.now(timezone.utc)
                session.add(outbox_item)
                session.commit()

                # Send via WebSocket
                asyncio.run(
                    websocket_manager.send_to_device(
                        outbox_item.device_id, outbox_item.payload
                    )
                )
                sent_count += 1

    return {"processed": processed_count, "sent": sent_count}


@celery_app.task
def process_sms_ack(outbox_id: str, status: str, error_message: str | None = None) -> dict:
    """
    Process the acknowledgment (ACK) from a device for a sent SMS.
    """
    with Session(engine) as session:
        outbox_item = session.get(SMSOutbox, uuid.UUID(outbox_id))
        if not outbox_item:
            return {"success": False, "error": "Outbox item not found"}

        # Update Outbox
        outbox_item.status = status
        if error_message:
            outbox_item.last_error = error_message
        session.add(outbox_item)

        # Update original SMSMessage
        message = session.get(SMSMessage, outbox_item.sms_message_id)
        if message:
            message.status = status
            if error_message:
                message.error_message = error_message
            if status == "sent":
                message.sent_at = datetime.now(timezone.utc)
            session.add(message)

        session.commit()

        return {"success": True, "outbox_id": outbox_id, "status": status}


@celery_app.task
def process_incoming_sms(
    user_id: str, from_number: str, body: str, timestamp: str | None = None
) -> dict:
    """Procesar SMS entrantes reportados por Android"""
    import asyncio

    async def _process():
        with Session(engine) as session:
            message = AndroidSMSProvider.process_incoming_sms(
                session=session,
                user_id=uuid.UUID(user_id),
                from_number=from_number,
                body=body,
                timestamp=timestamp,
            )

            # Buscar webhooks activos del usuario
            statement = (
                select(WebhookConfig)
                .where(WebhookConfig.user_id == uuid.UUID(user_id))
                .where(WebhookConfig.active is True)
            )
            webhooks = session.exec(statement).all()

            # Enviar webhooks de forma asíncrona
            webhook_results = []
            for webhook in webhooks:
                # Verificar si el evento está en la lista
                try:
                    events = json.loads(webhook.events)
                    if "sms_received" in events:
                        # Enviar webhook de forma asíncrona
                        send_webhook_notification.delay(
                            str(webhook.id), str(message.id)
                        )
                        webhook_results.append({"webhook_id": str(webhook.id)})
                except Exception:
                    pass

            return {
                "success": True,
                "message_id": str(message.id),
                "webhooks_sent": len(webhook_results),
            }

    return asyncio.run(_process())


@celery_app.task
def send_webhook_notification(webhook_id: str, message_id: str) -> dict:
    """Enviar notificación HTTP a webhook configurado cuando llega SMS"""
    import asyncio

    async def _send():
        with Session(engine) as session:
            webhook = session.get(WebhookConfig, uuid.UUID(webhook_id))
            if not webhook:
                return {"success": False, "error": "Webhook no encontrado"}

            message = session.get(SMSMessage, uuid.UUID(message_id))
            if not message:
                return {"success": False, "error": "Mensaje no encontrado"}

            result = await WebhookService.send_webhook(webhook, message)
            if result.get("success"):
                message.webhook_sent = True
                session.add(message)
                session.commit()

            return result

    return asyncio.run(_send())


@celery_app.task
def update_message_status(
    message_id: str, status: str, error_message: str | None = None
) -> dict:
    """Actualizar estado de mensajes"""
    with Session(engine) as session:
        message = session.get(SMSMessage, uuid.UUID(message_id))
        if not message:
            return {"success": False, "error": "Mensaje no encontrado"}

        message.status = status
        if error_message:
            message.error_message = error_message

        if status == "sent":
            message.sent_at = datetime.utcnow()
        elif status == "delivered":
            message.delivered_at = datetime.utcnow()

        session.add(message)
        session.commit()

        return {"success": True, "message_id": message_id, "status": status}


@celery_app.task
def retry_failed_messages() -> dict:
    """Reintentar mensajes fallidos"""
    with Session(engine) as session:
        # Buscar mensajes fallidos de las últimas 24 horas
        cutoff = datetime.utcnow() - timedelta(hours=24)
        statement = (
            select(SMSMessage)
            .where(SMSMessage.status == "failed")
            .where(SMSMessage.created_at >= cutoff)
            .where(SMSMessage.message_type == "outgoing")
            .limit(50)
        )
        messages = session.exec(statement).all()

        retried_count = 0
        for message in messages:
            message.status = "pending"
            session.add(message)
            retried_count += 1

        session.commit()

        # Disparar asignación
        assign_pending_messages.delay()

        return {"retried": retried_count}


@celery_app.task
def retry_webhook_delivery() -> dict:
    """Reintentar envío de webhooks fallidos"""
    # Esta tarea se puede implementar si guardamos intentos de webhook
    # Por ahora, los webhooks se reintentan en process_incoming_sms
    return {"success": True, "message": "Webhooks se procesan en tiempo real"}


@celery_app.task
def cleanup_offline_devices() -> dict:
    """Mark devices as offline if their last heartbeat is too old."""
    with Session(engine) as session:
        # Devices that are online but haven't sent a heartbeat in the last 5 minutes
        five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        statement = (
            select(SMSDevice)
            .where(SMSDevice.status == "online")
            .where(SMSDevice.last_heartbeat < five_minutes_ago)
        )
        offline_devices = session.exec(statement).all()

        for device in offline_devices:
            device.status = "offline"
            session.add(device)

        session.commit()
        return {"offline_count": len(offline_devices)}


@celery_app.task
def reset_monthly_quotas() -> dict:
    """Resetear contadores mensuales de SMS (tarea periódica)"""
    with Session(engine) as session:
        statement = select(UserQuota)
        quotas = session.exec(statement).all()

        reset_count = 0
        for quota in quotas:
            # Resetear si es el día configurado
            if quota.last_reset_date:
                if quota.last_reset_date.day == 1:  # Día 1 del mes
                    quota.sms_sent_this_month = 0
                    quota.last_reset_date = datetime.utcnow()
                    session.add(quota)
                    reset_count += 1

        session.commit()
        return {"reset_count": reset_count}


@celery_app.task
def check_user_quota(user_id: str, quota_type: str, count: int = 1) -> dict:
    """Verificar límites de usuario antes de operaciones"""
    from app.services.quota_service import QuotaService

    with Session(engine) as session:
        user_uuid = uuid.UUID(user_id)
        if quota_type == "sms":
            QuotaService.check_sms_quota(
                session=session, user_id=user_uuid, count=count
            )
        elif quota_type == "device":
            QuotaService.check_device_quota(session=session, user_id=user_uuid)

        return {"success": True, "quota_type": quota_type}
