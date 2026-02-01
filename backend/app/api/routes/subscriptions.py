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
from app.services.qstash_service import QStashService
from app.services.subscription_service import (
    SubscriptionService,
    get_subscription_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Payment Provider Callbacks
# ============================================================================


@router.post("/callback/authorize")
async def authorization_callback(
    session: SessionDep,
    user_uuid: str,
    remote_id: str,
) -> Any:
    """
    Callback from QvaPay after user authorizes automatic payments.

    This completes the authorization and charges the first payment.
    """
    try:
        user_id = uuid.UUID(remote_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid remote_id")

    service = get_subscription_service()
    subscription = await service.complete_authorization(
        session=session,
        user_id=user_id,
        provider_user_uuid=user_uuid,
    )

    return {
        "status": "success",
        "subscription_id": str(subscription.id),
        "subscription_status": subscription.status.value,
    }


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
