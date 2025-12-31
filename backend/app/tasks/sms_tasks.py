import json
import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.core.celery_app import celery_app
from app.core.db import engine
from app.models import SMSDevice, SMSMessage, UserQuota, WebhookConfig
from app.services.sms_service import AndroidSMSProvider
from app.services.webhook_service import WebhookService
from app.services.websocket_manager import websocket_manager


@celery_app.task
def assign_pending_messages() -> dict:
    """Asignar mensajes pendientes a dispositivos disponibles"""
    with Session(engine) as session:
        # Buscar mensajes pendientes
        statement = (
            select(SMSMessage)
            .where(SMSMessage.status == "pending")
            .where(SMSMessage.message_type == "outgoing")
            .order_by(SMSMessage.created_at)
            .limit(100)
        )
        messages = session.exec(statement).all()

        assigned_count = 0
        for message in messages:
            device = AndroidSMSProvider.assign_message_to_device(
                session=session, message=message
            )
            if device:
                # Marcar como asignado - el WebSocket lo enviará cuando esté conectado
                message.status = "assigned"
                session.add(message)
                assigned_count += 1

        session.commit()
        return {"assigned": assigned_count, "total": len(messages)}


@celery_app.task
def send_message_to_device(message_id: str, device_id: str) -> dict:
    """Marcar mensaje como asignado a dispositivo"""
    with Session(engine) as session:
        message = session.get(SMSMessage, uuid.UUID(message_id))
        if not message:
            return {"success": False, "error": "Mensaje no encontrado"}

        device = session.get(SMSDevice, uuid.UUID(device_id))
        if not device:
            return {"success": False, "error": "Dispositivo no encontrado"}

        # Asignar mensaje al dispositivo
        message.device_id = device.id
        message.status = "assigned"
        session.add(message)
        session.commit()

        # El WebSocket manager enviará el mensaje cuando el dispositivo esté conectado
        return {"success": True, "message_id": message_id, "device_id": device_id}


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
    """Marcar dispositivos offline si no hay conexión WebSocket activa"""
    with Session(engine) as session:
        statement = select(SMSDevice).where(SMSDevice.status == "online")
        devices = session.exec(statement).all()

        offline_count = 0
        for device in devices:
            # Verificar si está conectado vía WebSocket
            if not websocket_manager.is_device_connected(device.id):
                # Verificar último heartbeat
                if device.last_heartbeat:
                    timeout = datetime.utcnow() - timedelta(seconds=300)  # 5 minutos
                    if device.last_heartbeat < timeout:
                        device.status = "offline"
                        session.add(device)
                        offline_count += 1
                else:
                    device.status = "offline"
                    session.add(device)
                    offline_count += 1

        session.commit()
        return {"offline_count": offline_count}


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
