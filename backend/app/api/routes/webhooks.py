import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    WebhookConfigCreate,
    WebhookConfigPublic,
    WebhookConfigsPublic,
    WebhookConfigUpdate,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=WebhookConfigPublic
)
def create_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_in: WebhookConfigCreate,
) -> WebhookConfigPublic:
    """Create/configure webhook"""
    webhook = crud.create_webhook_config(
        session=session, webhook_in=webhook_in, user_id=current_user.id
    )
    return WebhookConfigPublic.model_validate(webhook)


@router.get("", response_model=WebhookConfigsPublic)
def list_webhooks(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> WebhookConfigsPublic:
    """List configured webhooks"""
    webhooks = crud.get_webhook_configs_by_user(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return WebhookConfigsPublic(
        data=[WebhookConfigPublic.model_validate(w) for w in webhooks],
        count=len(webhooks),
    )


@router.get("/{webhook_id}", response_model=WebhookConfigPublic)
def get_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_id: uuid.UUID,
) -> WebhookConfigPublic:
    """Get specific webhook"""
    webhook = crud.get_webhook_config(session=session, webhook_id=webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )
    return WebhookConfigPublic.model_validate(webhook)


@router.put("/{webhook_id}", response_model=WebhookConfigPublic)
def update_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_id: uuid.UUID,
    webhook_in: WebhookConfigUpdate,
) -> WebhookConfigPublic:
    """Update webhook"""
    webhook = crud.get_webhook_config(session=session, webhook_id=webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )
    webhook = crud.update_webhook_config(
        session=session, db_webhook=webhook, webhook_in=webhook_in
    )
    return WebhookConfigPublic.model_validate(webhook)


@router.delete("/{webhook_id}", response_model=Message)
def delete_webhook(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    webhook_id: uuid.UUID,
) -> Message:
    """Delete webhook"""
    webhook = crud.get_webhook_config(session=session, webhook_id=webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )
    crud.delete_webhook_config(session=session, webhook_id=webhook_id)
    return Message(message="Webhook deleted")
