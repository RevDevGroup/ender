"""
Subscription management API routes.

Endpoints for managing user subscriptions, payments, and renewal jobs.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core.config import settings
from app.models import (
    Payment,
    PaymentPublic,
    PaymentsPublic,
    PaymentStatus,
    Subscription,
    SubscriptionCreate,
    SubscriptionCreateResponse,
    SubscriptionPublic,
    SubscriptionStatus,
    SubscriptionWithPlan,
    User,
    UserPlan,
    UserPlanPublic,
    UserPlansPublic,
)
from app.services.payment import get_payment_service
from app.services.qstash_service import QStashService
from app.services.subscription_service import (
    SubscriptionService,
    get_subscription_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Public Plan Endpoints
# ============================================================================


@router.get("/plans", response_model=UserPlansPublic)
def list_available_plans(session: SessionDep) -> Any:
    """
    List all publicly available subscription plans.
    """
    plans = session.exec(
        select(UserPlan)
        .where(UserPlan.is_public == True)  # noqa: E712
        .order_by(UserPlan.price)  # type: ignore[arg-type]
    ).all()
    return UserPlansPublic(data=plans, count=len(plans))


@router.get("/plans/{plan_id}", response_model=UserPlanPublic)
def get_plan(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """
    Get details of a specific plan.
    """
    plan = session.get(UserPlan, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    return plan


# ============================================================================
# Subscription Management Endpoints
# ============================================================================


@router.post("/subscribe", response_model=SubscriptionCreateResponse)
async def create_subscription(
    subscription_in: SubscriptionCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Create a new subscription for the current user.

    Returns a payment URL where the user can complete the payment.
    For free plans, the subscription is activated immediately.
    """
    service = get_subscription_service()
    subscription, payment, payment_url = await service.create_subscription(
        session=session,
        user_id=current_user.id,
        plan_id=subscription_in.plan_id,
        billing_cycle=subscription_in.billing_cycle,
    )

    if payment is None:
        # Free plan - no payment needed
        return SubscriptionCreateResponse(
            subscription_id=subscription.id,
            payment_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            payment_url=None,
            amount=0.0,
            message="Free plan activated successfully",
        )

    return SubscriptionCreateResponse(
        subscription_id=subscription.id,
        payment_id=payment.id,
        payment_url=payment_url,
        amount=payment.amount,
        message="Complete the payment to activate your subscription",
    )


@router.get("/my-subscription", response_model=SubscriptionWithPlan | None)
def get_my_subscription(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Get the current user's active subscription with plan details.
    """
    subscription = session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).first()

    if not subscription:
        return None

    # Manually construct response with plan
    plan = subscription.plan
    return SubscriptionWithPlan(
        id=subscription.id,
        user_id=subscription.user_id,
        plan_id=subscription.plan_id,
        billing_cycle=subscription.billing_cycle,
        status=subscription.status,
        cancel_at_period_end=subscription.cancel_at_period_end,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        canceled_at=subscription.canceled_at,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
        plan=UserPlanPublic(
            id=plan.id,
            name=plan.name,
            max_sms_per_month=plan.max_sms_per_month,
            max_devices=plan.max_devices,
            price=plan.price,
            price_yearly=plan.price_yearly,
            is_public=plan.is_public,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        ),
    )


@router.post("/verify-payment/{payment_id}", response_model=SubscriptionPublic)
async def verify_payment(
    payment_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Verify if a payment was completed and activate the subscription.

    Call this after the user returns from the payment provider.
    """
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    # Verify ownership
    if payment.subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to verify this payment",
        )

    if payment.status == PaymentStatus.COMPLETED:
        return payment.subscription

    service = get_subscription_service()
    subscription = await service.verify_and_process_payment(
        session=session,
        payment_id=payment_id,
    )

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment not completed yet",
        )

    return subscription


@router.post("/cancel", response_model=SubscriptionPublic)
def cancel_subscription(
    session: SessionDep,
    current_user: CurrentUser,
    immediate: bool = False,
) -> Any:
    """
    Cancel the current user's subscription.

    By default, cancellation takes effect at the end of the current billing period.
    Set immediate=true to cancel immediately (no refund).
    """
    subscription = session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )

    return SubscriptionService.cancel_subscription(
        session=session,
        subscription_id=subscription.id,
        immediate=immediate,
    )


@router.get("/payments", response_model=PaymentsPublic)
def get_payment_history(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
) -> Any:
    """
    Get the current user's payment history.
    """
    subscription = session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).first()

    if not subscription:
        return PaymentsPublic(data=[], count=0)

    payments = list(
        session.exec(
            select(Payment)
            .where(Payment.subscription_id == subscription.id)
            .offset(skip)
            .limit(limit)
        ).all()
    )
    # Sort by created_at descending
    payments.sort(key=lambda p: p.created_at, reverse=True)

    return PaymentsPublic(data=payments, count=len(payments))


@router.get("/payments/{payment_id}", response_model=PaymentPublic)
def get_payment(
    payment_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Get details of a specific payment.
    """
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    # Verify ownership
    if payment.subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment",
        )

    return payment


# ============================================================================
# Job Endpoints (called by QStash)
# ============================================================================


@router.post("/jobs/check-renewals")
async def check_renewals_job(
    request: Request,
    session: SessionDep,
) -> Any:
    """
    Check for expiring subscriptions and generate renewal invoices.

    This endpoint is called daily by QStash Schedule.
    """
    # Verify QStash signature
    signature = request.headers.get("Upstash-Signature", "")
    body = await request.body()
    url = str(request.url)

    if not QStashService.verify_signature(body, signature, url):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid QStash signature",
        )

    now = datetime.now(UTC)
    results: dict[str, Any] = {
        "checked_at": now.isoformat(),
        "renewals_generated": 0,
        "subscriptions_expired": 0,
        "errors": [],
    }

    service = get_subscription_service()
    reminder_days = getattr(settings, "RENEWAL_REMINDER_DAYS", 3)
    grace_days = getattr(settings, "SUBSCRIPTION_GRACE_PERIOD_DAYS", 3)

    # 1. Generate invoices for subscriptions expiring soon
    threshold = now + timedelta(days=reminder_days)
    expiring = session.exec(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end <= threshold,
            Subscription.current_period_end > now,
            Subscription.cancel_at_period_end == False,  # noqa: E712
        )
    ).all()

    for subscription in expiring:
        # Check if already has pending payment
        pending_payment = session.exec(
            select(Payment).where(
                Payment.subscription_id == subscription.id,
                Payment.status == PaymentStatus.PENDING,
            )
        ).first()

        if not pending_payment:
            try:
                payment, payment_url = await service.generate_renewal_invoice(
                    session, subscription.id
                )
                # Enqueue renewal email via QStash
                QStashService.enqueue(
                    endpoint="/api/v1/subscriptions/jobs/send-renewal-email",
                    payload={
                        "user_id": str(subscription.user_id),
                        "payment_id": str(payment.id),
                        "payment_url": payment_url or "",
                    },
                    deduplication_id=f"renewal-email-{payment.id}",
                )
                results["renewals_generated"] += 1
            except Exception as e:
                error_msg = f"subscription {subscription.id}: {e!s}"
                results["errors"].append(error_msg)
                logger.exception(error_msg)

    # 2. Expire subscriptions past grace period
    grace_period = timedelta(days=grace_days)
    expired = session.exec(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.PAST_DUE,
            Subscription.current_period_end < now - grace_period,
        )
    ).all()

    for subscription in expired:
        try:
            SubscriptionService.expire_subscription(session, subscription.id)
            results["subscriptions_expired"] += 1
        except Exception as e:
            error_msg = f"expire {subscription.id}: {e!s}"
            results["errors"].append(error_msg)
            logger.exception(error_msg)

    logger.info(f"Renewal job completed: {results}")
    return results


@router.post("/jobs/send-renewal-email")
async def send_renewal_email_job(
    request: Request,
    session: SessionDep,
) -> Any:
    """
    Send renewal reminder email.

    Called by QStash queue after generating a renewal invoice.
    """
    # Verify QStash signature
    signature = request.headers.get("Upstash-Signature", "")
    body = await request.body()
    url = str(request.url)

    if not QStashService.verify_signature(body, signature, url):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid QStash signature",
        )

    payload = await request.json()
    user_id = uuid.UUID(payload["user_id"])
    payment_url = payload.get("payment_url", "")

    user = session.get(User, user_id)
    if not user:
        logger.warning(f"User not found for renewal email: {user_id}")
        return {"status": "skipped", "reason": "user not found"}

    # TODO: Send email using email service
    # For now, just log
    logger.info(
        f"Would send renewal email to {user.email} with payment URL: {payment_url}"
    )

    return {"status": "sent"}


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.post(
    "/admin/schedules/renewal",
    dependencies=[Depends(get_current_active_superuser)],
)
def manage_renewal_schedule(
    action: str,  # "create", "delete", or "status"
) -> Any:
    """
    Manage the renewal check schedule (superuser only).

    Actions:
    - create: Create or update the daily renewal schedule
    - delete: Delete the renewal schedule
    - status: Get current schedule status
    """
    if action == "create":
        schedule_id = QStashService.create_renewal_schedule()
        return {"action": "created", "schedule_id": schedule_id}
    elif action == "delete":
        success = QStashService.delete_renewal_schedule()
        return {"action": "deleted", "success": success}
    elif action == "status":
        schedule = QStashService.get_renewal_schedule()
        return {"schedule": schedule}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use: create, delete, or status",
        )


@router.get(
    "/admin/provider-balance",
    dependencies=[Depends(get_current_active_superuser)],
)
async def get_provider_balance() -> Any:
    """
    Get the current balance from the payment provider (superuser only).
    """
    service = get_payment_service()
    balance = await service.get_balance()
    return {
        "provider": service.provider_name,
        "balance": balance,
        "configured": service.is_configured(),
    }
