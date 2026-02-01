"""
Subscription callbacks and jobs.

Internal endpoints for payment provider callbacks and QStash background jobs.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import (
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
)
from app.services.payment import get_payment_service
from app.services.payment.base import WebhookEventType
from app.services.qstash_service import QStashService
from app.services.subscription_service import (
    SubscriptionService,
    get_subscription_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Payment Provider Webhooks (Generic)
# ============================================================================


@router.post("/webhook/{provider}")
@router.get("/webhook/{provider}")
async def payment_webhook(
    provider: str,
    request: Request,
    session: SessionDep,
) -> Any:
    """
    Generic webhook endpoint for payment providers.

    Supports:
    - QvaPay authorize_payments callback (GET with query params)
    - QvaPay invoice webhook (POST with JSON)
    - Future providers (TropiPay, etc.)

    Args:
        provider: Payment provider name (qvapay, tropipay)
    """
    payment_service = get_payment_service()

    # Get payload based on request method
    if request.method == "GET":
        payload: dict[str, object] = dict(request.query_params)
    else:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Parse webhook using the provider's logic
    try:
        event = payment_service.parse_webhook(
            provider_name=provider,
            payload=payload,
            headers=dict(request.headers),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not event:
        logger.warning(f"Unrecognized webhook from {provider}: {payload}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    logger.info(f"Webhook received from {provider}: {event.event_type.value}")

    service = get_subscription_service()

    if event.event_type == WebhookEventType.AUTHORIZATION_COMPLETED:
        # Handle authorize_payments callback
        if not event.user_uuid:
            raise HTTPException(status_code=400, detail="Missing user_uuid")

        try:
            user_id = uuid.UUID(event.remote_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid remote_id")

        subscription = await service.complete_authorization(
            session=session,
            user_id=user_id,
            provider_user_uuid=event.user_uuid,
        )

        return {
            "status": "success",
            "event": "authorization_completed",
            "subscription_id": str(subscription.id),
            "subscription_status": subscription.status.value,
        }

    elif event.event_type == WebhookEventType.PAYMENT_COMPLETED:
        # Handle invoice payment webhook
        if not event.transaction_id:
            raise HTTPException(status_code=400, detail="Missing transaction_id")

        try:
            payment_id = uuid.UUID(event.remote_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid remote_id")

        subscription = await service.complete_invoice_payment(
            session=session,
            payment_id=payment_id,
            transaction_id=event.transaction_id,
        )

        return {
            "status": "success",
            "event": "payment_completed",
            "subscription_id": str(subscription.id),
            "subscription_status": subscription.status.value,
        }

    else:
        logger.warning(f"Unhandled webhook event type: {event.event_type}")
        return {"status": "ignored", "event": event.event_type.value}


# ============================================================================
# Background Jobs (called by QStash)
# ============================================================================


@router.post("/jobs/check-renewals")
async def check_renewals_job(
    request: Request,
    session: SessionDep,
) -> Any:
    """
    Check for expiring subscriptions and process automatic renewals.

    Called daily by QStash Schedule.
    """
    signature = request.headers.get("Upstash-Signature", "")
    body = await request.body()
    url = str(request.url)

    if not QStashService.verify_signature(body, signature, url):
        raise HTTPException(status_code=401, detail="Invalid signature")

    now = datetime.now(UTC)
    results: dict[str, Any] = {
        "checked_at": now.isoformat(),
        "renewals_success": 0,
        "renewals_failed": 0,
        "expired": 0,
        "errors": [],
    }

    service = get_subscription_service()
    reminder_days = getattr(settings, "RENEWAL_REMINDER_DAYS", 3)
    grace_days = getattr(settings, "SUBSCRIPTION_GRACE_PERIOD_DAYS", 3)

    # Process expiring subscriptions (only those with auto-renewal)
    threshold = now + timedelta(days=reminder_days)
    expiring = session.exec(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end <= threshold,
            Subscription.current_period_end > now,
            Subscription.cancel_at_period_end == False,  # noqa: E712
            Subscription.provider_user_uuid.isnot(None),  # type: ignore[union-attr]
        )
    ).all()

    for subscription in expiring:
        # Check if already has pending payment
        pending = session.exec(
            select(Payment).where(
                Payment.subscription_id == subscription.id,
                Payment.status == PaymentStatus.PENDING,
            )
        ).first()

        if not pending:
            try:
                payment = await service.process_renewal(session, subscription.id)
                if payment.status == PaymentStatus.COMPLETED:
                    results["renewals_success"] += 1
                else:
                    results["renewals_failed"] += 1
            except Exception as e:
                results["errors"].append(f"{subscription.id}: {e!s}")
                logger.exception(f"Renewal error for {subscription.id}")

    # Expire past-due subscriptions after grace period
    grace_period = timedelta(days=grace_days)
    past_due = session.exec(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.PAST_DUE,
            Subscription.current_period_end < now - grace_period,
        )
    ).all()

    for subscription in past_due:
        try:
            SubscriptionService.expire_subscription(session, subscription.id)
            results["expired"] += 1
        except Exception as e:
            results["errors"].append(f"expire {subscription.id}: {e!s}")

    logger.info(f"Renewal job completed: {results}")
    return results
