import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    PlanUpgrade,
    SMSBulkCreate,
    SMSDeviceCreate,
    SMSDevicePublic,
    SMSDeviceUpdate,
    SMSMessageCreate,
    SMSMessagePublic,
    UserPlan,
    UserPlanPublic,
    WebhookConfigCreate,
    WebhookConfigPublic,
    WebhookConfigUpdate,
)
from app.services.quota_service import QuotaService
from app.tasks.sms_tasks import assign_pending_messages

router = APIRouter(prefix="/sms", tags=["sms"])


# Envío y gestión de SMS
@router.post("/send", status_code=status.HTTP_201_CREATED)
def send_sms(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    message_in: SMSMessageCreate,
) -> dict[str, Any]:
    """Enviar SMS individual"""
    # Validar límites
    QuotaService.check_sms_quota(session=session, user_id=current_user.id, count=1)

    # Crear mensaje
    message = crud.create_sms_message(
        session=session, message_in=message_in, user_id=current_user.id
    )

    # Incrementar contador
    QuotaService.increment_sms_count(session=session, user_id=current_user.id, count=1)

    # Disparar asignación
    assign_pending_messages.delay()

    return {
        "success": True,
        "message_id": str(message.id),
        "status": message.status,
    }


@router.post("/send-bulk", status_code=status.HTTP_201_CREATED)
def send_bulk_sms(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    bulk_in: SMSBulkCreate,
) -> dict[str, Any]:
    """Enviar SMS a múltiples destinatarios"""
    # Validar límites
    QuotaService.check_sms_quota(
        session=session, user_id=current_user.id, count=len(bulk_in.recipients)
    )

    # Crear mensajes
    message_ids = []
    for recipient in bulk_in.recipients:
        message_in = SMSMessageCreate(
            to=recipient, body=bulk_in.body, device_id=bulk_in.device_id
        )
        message = crud.create_sms_message(
            session=session, message_in=message_in, user_id=current_user.id
        )
        message_ids.append(str(message.id))

    # Incrementar contador
    QuotaService.increment_sms_count(
        session=session, user_id=current_user.id, count=len(bulk_in.recipients)
    )

    # Disparar asignación
    assign_pending_messages.delay()

    return {
        "success": True,
        "total_recipients": len(bulk_in.recipients),
        "status": "processing",
        "message_ids": message_ids,
    }


@router.get("/messages")
def list_messages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    message_type: str | None = Query(None),
) -> dict[str, Any]:
    """Listar mensajes del usuario"""
    messages = crud.get_sms_messages_by_user(
        session=session,
        user_id=current_user.id,
        message_type=message_type,
        skip=skip,
        limit=limit,
    )
    return {
        "success": True,
        "data": [SMSMessagePublic.model_validate(m) for m in messages],
        "count": len(messages),
    }


@router.get("/messages/{message_id}")
def get_message(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    message_id: uuid.UUID,
) -> dict[str, Any]:
    """Obtener mensaje específico"""
    message = crud.get_sms_message(session=session, message_id=message_id)
    if not message or message.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mensaje no encontrado"
        )
    return {"success": True, "data": SMSMessagePublic.model_validate(message)}


@router.get("/incoming")
def list_incoming_messages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """Listar SMS recibidos"""
    messages = crud.get_sms_messages_by_user(
        session=session,
        user_id=current_user.id,
        message_type="incoming",
        skip=skip,
        limit=limit,
    )
    return {
        "success": True,
        "data": [SMSMessagePublic.model_validate(m) for m in messages],
        "count": len(messages),
    }


# Gestión de planes y límites
@router.get("/plans")
def list_plans(*, session: SessionDep) -> dict[str, Any]:
    """Listar planes disponibles"""

    statement = select(UserPlan)
    plans = session.exec(statement).all()
    return {
        "success": True,
        "data": [UserPlanPublic.model_validate(p) for p in plans],
    }


@router.get("/quota")
def get_quota(*, session: SessionDep, current_user: CurrentUser) -> dict[str, Any]:
    """Obtener información de cuota actual del usuario"""
    quota_info = QuotaService.get_user_quota(session=session, user_id=current_user.id)
    return {"success": True, "data": quota_info}


@router.put("/quota/upgrade")
def upgrade_plan(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    upgrade_in: PlanUpgrade,
) -> dict[str, Any]:
    """Cambiar plan del usuario (requiere superuser o integración de pago)"""
    from app.api.deps import get_current_active_superuser

    # Por ahora, solo superusers pueden cambiar planes
    # En el futuro, aquí se integraría con sistema de pagos
    get_current_active_superuser(current_user)

    plan = session.get(UserPlan, upgrade_in.plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado"
        )

    # Obtener o crear quota
    quota = current_user.quota
    if not quota:
        from app.services.quota_service import QuotaService

        quota = QuotaService._create_default_quota(
            session=session, user_id=current_user.id
        )

    # Actualizar plan
    quota.plan_id = upgrade_in.plan_id
    session.add(quota)
    session.commit()
    session.refresh(quota)

    return {
        "success": True,
        "message": f"Plan actualizado a {plan.name}",
        "data": {"plan": plan.name, "plan_id": str(upgrade_in.plan_id)},
    }


# Gestión de dispositivos
@router.post("/devices", status_code=status.HTTP_201_CREATED)
def create_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_in: SMSDeviceCreate,
) -> dict[str, Any]:
    """Registrar nuevo dispositivo"""
    # Validar límite de dispositivos
    QuotaService.check_device_quota(session=session, user_id=current_user.id)

    # Crear dispositivo
    device = crud.create_sms_device(
        session=session, device_in=device_in, user_id=current_user.id
    )

    # Incrementar contador
    QuotaService.increment_device_count(session=session, user_id=current_user.id)

    return {
        "success": True,
        "data": {
            "device_id": str(device.id),
            "api_key": device.api_key,
            "status": device.status,
        },
    }


@router.get("/devices")
def list_devices(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """Listar dispositivos del usuario"""
    devices = crud.get_sms_devices_by_user(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return {
        "success": True,
        "data": [SMSDevicePublic.model_validate(d) for d in devices],
        "count": len(devices),
    }


@router.get("/devices/{device_id}")
def get_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_id: uuid.UUID,
) -> dict[str, Any]:
    """Obtener dispositivo específico"""
    device = crud.get_sms_device(session=session, device_id=device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado"
        )
    return {"success": True, "data": SMSDevicePublic.model_validate(device)}


@router.put("/devices/{device_id}")
def update_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_id: uuid.UUID,
    device_in: SMSDeviceUpdate,
) -> dict[str, Any]:
    """Actualizar dispositivo"""
    device = crud.get_sms_device(session=session, device_id=device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado"
        )
    device = crud.update_sms_device(
        session=session, db_device=device, device_in=device_in
    )
    return {"success": True, "data": SMSDevicePublic.model_validate(device)}


@router.delete("/devices/{device_id}")
def delete_device(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    device_id: uuid.UUID,
) -> Message:
    """Eliminar dispositivo"""
    device = crud.get_sms_device(session=session, device_id=device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado"
        )
    crud.delete_sms_device(session=session, device_id=device_id)
    # Decrementar contador
    QuotaService.decrement_device_count(session=session, user_id=current_user.id)
    return Message(message="Dispositivo eliminado")


# Gestión de webhooks
@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
def create_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_in: WebhookConfigCreate,
) -> dict[str, Any]:
    """Crear/configurar webhook"""
    webhook = crud.create_webhook_config(
        session=session, webhook_in=webhook_in, user_id=current_user.id
    )
    return {"success": True, "data": WebhookConfigPublic.model_validate(webhook)}


@router.get("/webhooks")
def list_webhooks(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """Listar webhooks configurados"""
    webhooks = crud.get_webhook_configs_by_user(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return {
        "success": True,
        "data": [WebhookConfigPublic.model_validate(w) for w in webhooks],
        "count": len(webhooks),
    }


@router.get("/webhooks/{webhook_id}")
def get_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_id: uuid.UUID,
) -> dict[str, Any]:
    """Obtener webhook específico"""
    webhook = crud.get_webhook_config(session=session, webhook_id=webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook no encontrado"
        )
    return {"success": True, "data": WebhookConfigPublic.model_validate(webhook)}


@router.put("/webhooks/{webhook_id}")
def update_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_id: uuid.UUID,
    webhook_in: WebhookConfigUpdate,
) -> dict[str, Any]:
    """Actualizar webhook"""
    webhook = crud.get_webhook_config(session=session, webhook_id=webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook no encontrado"
        )
    webhook = crud.update_webhook_config(
        session=session, db_webhook=webhook, webhook_in=webhook_in
    )
    return {"success": True, "data": WebhookConfigPublic.model_validate(webhook)}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_id: uuid.UUID,
) -> Message:
    """Eliminar webhook"""
    webhook = crud.get_webhook_config(session=session, webhook_id=webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook no encontrado"
        )
    crud.delete_webhook_config(session=session, webhook_id=webhook_id)
    return Message(message="Webhook eliminado")
