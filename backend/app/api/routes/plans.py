from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import (
    PlanUpgrade,
    PlanUpgradePublic,
    UserPlan,
    UserPlanPublic,
    UserPlansPublic,
    UserQuotaPublic,
)
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/list", response_model=UserPlansPublic)
def list_plans(*, session: SessionDep) -> UserPlansPublic:
    """List available plans"""
    statement = select(UserPlan)
    plans = session.exec(statement).all()
    return UserPlansPublic(
        data=[UserPlanPublic.model_validate(p) for p in plans], count=len(plans)
    )


@router.get("/quota", response_model=UserQuotaPublic)
def get_quota(*, session: SessionDep, current_user: CurrentUser) -> UserQuotaPublic:
    """Get user quota information"""
    quota_info = QuotaService.get_user_quota(session=session, user_id=current_user.id)
    return UserQuotaPublic.model_validate(quota_info)


@router.put("/upgrade", response_model=PlanUpgradePublic)
def upgrade_plan(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    upgrade_in: PlanUpgrade,
) -> PlanUpgradePublic:
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

    return PlanUpgradePublic(
        message=f"Plan updated to {plan.name}",
        data={"plan": plan.name, "plan_id": str(upgrade_in.plan_id)},
    )
