import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlmodel import col, delete, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.rate_limit import RateLimits, limiter
from app.core.security import get_password_hash, verify_password
from app.models import (
    Message,
    SMSMessage,
    UpdatePassword,
    User,
    UserCreate,
    UserPlanInfo,
    UserPublic,
    UserPublicWithPlan,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.services.email import get_email_service
from app.utils import (
    generate_email_verification_email,
    generate_email_verification_token,
    generate_new_account_email,
    send_email,
    verify_email_verification_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()
    user_public_list = [UserPublic.model_validate(user) for user in users]

    return UsersPublic(data=user_public_list, count=count)


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublicWithPlan)
def read_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get current user with plan information.
    """
    # Refresh to load relationships
    session.refresh(current_user)
    plan_info = None

    # Get plan info from quota or subscription
    if current_user.quota and current_user.quota.plan:
        plan = current_user.quota.plan
        plan_info = UserPlanInfo(
            plan_name=plan.name,
            max_sms_per_month=plan.max_sms_per_month,
            max_devices=plan.max_devices,
            sms_sent_this_month=current_user.quota.sms_sent_this_month,
            devices_registered=current_user.quota.devices_registered,
        )

        # Add subscription info if exists
        if current_user.subscription:
            sub = current_user.subscription
            plan_info.subscription_status = sub.status.value
            plan_info.subscription_ends_at = sub.current_period_end
            plan_info.has_auto_renewal = bool(sub.provider_user_uuid)

    return UserPublicWithPlan(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        plan=plan_info,
    )


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


async def send_verification_email_task(email: str) -> None:
    """Background task to send verification email."""
    try:
        token = generate_email_verification_token(email)
        email_data = generate_email_verification_email(email_to=email, token=token)
        email_service = get_email_service()
        await email_service.send_email(
            to=email,
            subject=email_data.subject,
            html_content=email_data.html_content,
            tags=["verification"],
        )
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")


@router.post("/signup", response_model=UserPublic)
@limiter.limit(RateLimits.AUTH_SIGNUP)
async def register_user(
    request: Request,  # noqa: ARG001 - Required by SlowAPI limiter
    session: SessionDep,
    user_in: UserRegister,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Create new user without the need to be logged in.

    A verification email will be sent to the user's email address.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)

    # Send verification email in background
    if settings.emails_enabled:
        background_tasks.add_task(send_verification_email_task, user.email)

    return user


@router.post("/verify-email", response_model=Message)
@limiter.limit(RateLimits.AUTH_EMAIL_VERIFICATION)
def verify_email(
    request: Request,  # noqa: ARG001 - Required by SlowAPI limiter
    session: SessionDep,
    token: str,
) -> Any:
    """
    Verify user email with token from verification email.
    """
    email = verify_email_verification_token(token)
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token",
        )

    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if user.email_verified:
        return Message(message="Email already verified")

    user.email_verified = True
    user.email_verified_at = datetime.now(UTC)
    session.add(user)
    session.commit()

    return Message(message="Email verified successfully")


@router.post("/resend-verification", response_model=Message)
@limiter.limit(RateLimits.AUTH_EMAIL_VERIFICATION)
async def resend_verification_email(
    request: Request,  # noqa: ARG001 - Required by SlowAPI limiter
    session: SessionDep,
    email: str,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Resend verification email.
    """
    user = crud.get_user_by_email(session=session, email=email)

    # Always return success to prevent email enumeration
    if not user or user.email_verified:
        return Message(
            message="If the email exists and is not verified, a verification email has been sent"
        )

    if settings.emails_enabled:
        background_tasks.add_task(send_verification_email_task, email)

    return Message(
        message="If the email exists and is not verified, a verification email has been sent"
    )


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    statement = delete(SMSMessage).where(col(SMSMessage.user_id) == user_id)
    session.exec(statement)  # type: ignore
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
