from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import (
    PlanUpgrade,
    UserPlan,
    UserPlanPublic,
)
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/list")
def list_plans(*, session: SessionDep) -> dict[str, Any]:
    """List available plans"""
    statement = select(UserPlan)
    plans = session.exec(statement).all()
    return {
        "success": True,
        "data": [UserPlanPublic.model_validate(p) for p in plans],
    }


@router.get("/quota")
def get_quota(*, session: SessionDep, current_user: CurrentUser) -> dict[str, Any]:
    """Get user quota information"""
    quota_info = QuotaService.get_user_quota(session=session, user_id=current_user.id)
    return {"success": True, "data": quota_info}


@router.put("/upgrade")
def upgrade_plan(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    upgrade_in: PlanUpgrade,
) -> dict[str, Any]:
    """Change user plan (requires superuser or payment integration)"""
    # TODO: For now, only superusers can change plans
    # In the future, here will be integrated with payment system
    get_current_active_superuser(current_user)

    plan = session.get(UserPlan, upgrade_in.plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    # Get or create quota
    quota = current_user.quota
    if not quota:
        quota = QuotaService._create_default_quota(
            session=session, user_id=current_user.id
        )

    # Update plan
    quota.plan_id = upgrade_in.plan_id
    session.add(quota)
    session.commit()
    session.refresh(quota)

    return {
        "success": True,
        "message": f"Plan updated to {plan.name}",
        "data": {"plan": plan.name, "plan_id": str(upgrade_in.plan_id)},
    }
