"""
Plan management API routes.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import (
    BillingCycle,
    Subscription,
    UserPlan,
    UserPlanPublic,
    UserPlansPublic,
    UserQuotaPublic,
)
from app.services.quota_service import QuotaService
from app.services.subscription_service import (
    SubscriptionService,
    get_subscription_service,
)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/list", response_model=UserPlansPublic)
def list_plans(*, session: SessionDep) -> UserPlansPublic:
    """List available plans."""
    plans = session.exec(
        select(UserPlan)
        .where(UserPlan.is_public == True)  # noqa: E712
        .order_by(UserPlan.price)  # type: ignore[arg-type]
    ).all()
    return UserPlansPublic(
        data=[UserPlanPublic.model_validate(p) for p in plans], count=len(plans)
    )


@router.get("/quota", response_model=UserQuotaPublic)
def get_quota(*, session: SessionDep, current_user: CurrentUser) -> UserQuotaPublic:
    """Get user quota information."""
    quota_info = QuotaService.get_user_quota(session=session, user_id=current_user.id)
    return UserQuotaPublic.model_validate(quota_info)


@router.put("/upgrade")
async def upgrade_plan(
    request: Request,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    plan_id: uuid.UUID,
    billing_cycle: BillingCycle = BillingCycle.MONTHLY,
) -> Any:
    """
    Upgrade to a new plan.

    - Free plans: activates immediately
    - Paid plans: returns authorization URL for automatic payments

    After authorizing, the first payment is charged automatically.
    """
    plan = session.get(UserPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not plan.is_public:
        raise HTTPException(status_code=400, detail="Plan not available")

    # Build callback URL from request (server-to-server)
    base_url = str(request.base_url).rstrip("/")
    callback_url = f"{base_url}/api/v1/subscriptions/callback/authorize"

    # Build success/error URLs for user redirect (frontend)
    frontend_url = settings.FRONTEND_HOST.rstrip("/")
    success_url = f"{frontend_url}/subscription/success"
    error_url = f"{frontend_url}/subscription/error"

    service = get_subscription_service()
    subscription, authorization_url = await service.start_subscription(
        session=session,
        user_id=current_user.id,
        plan_id=plan_id,
        billing_cycle=billing_cycle,
        callback_url=callback_url,
        success_url=success_url,
        error_url=error_url,
    )

    if authorization_url is None:
        # Free plan - activated immediately
        return {
            "status": "activated",
            "plan": plan.name,
            "message": "Plan activated successfully",
        }

    # Paid plan - redirect to authorize
    return {
        "status": "pending_authorization",
        "plan": plan.name,
        "authorization_url": authorization_url,
        "message": "Authorize automatic payments to activate plan",
    }


@router.post("/cancel")
def cancel_plan(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    immediate: bool = False,
) -> Any:
    """
    Cancel subscription.

    By default, cancels at end of current billing period.
    Set immediate=true to cancel immediately (no refund).
    """
    subscription = session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")

    SubscriptionService.cancel_subscription(
        session=session,
        subscription_id=subscription.id,
        immediate=immediate,
    )

    if immediate:
        return {"status": "canceled", "message": "Subscription canceled immediately"}

    return {
        "status": "pending_cancellation",
        "ends_at": subscription.current_period_end.isoformat(),
        "message": "Subscription will cancel at end of billing period",
    }
