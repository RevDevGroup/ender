"""
Subscription management service.

Handles subscription lifecycle with automatic payments only.
Uses QvaPay authorize_payments + charge for all paid subscriptions.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import (
    BillingCycle,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    UserPlan,
    UserQuota,
)
from app.services.payment import PaymentService, get_payment_service

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service for managing user subscriptions with automatic payments.

    Flow for paid plans:
    1. User requests upgrade → get authorization URL
    2. User authorizes on QvaPay → callback saves provider_user_uuid
    3. First charge is made automatically
    4. Renewals are charged automatically
    """

    def __init__(self, payment_service: PaymentService | None = None):
        self._payment_service = payment_service

    @property
    def payment_service(self) -> PaymentService:
        if self._payment_service is None:
            self._payment_service = get_payment_service()
        return self._payment_service

    async def start_subscription(
        self,
        session: Session,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        billing_cycle: BillingCycle,
        callback_url: str,
        success_url: str,
        error_url: str,
    ) -> tuple[Subscription | None, str | None]:
        """
        Start subscription process.

        For free plans: activates immediately, returns (subscription, None)
        For paid plans: returns (subscription, authorization_url)

        The subscription stays PENDING until authorization callback + first charge.
        """
        # Check for existing active subscription
        existing = session.exec(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()
        if existing and existing.status in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PENDING,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active subscription",
            )

        plan = session.get(UserPlan, plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )

        if not plan.is_public:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan not available",
            )

        # Calculate amount
        if billing_cycle == BillingCycle.MONTHLY:
            amount = plan.price
        else:
            amount = plan.price_yearly if plan.price_yearly > 0 else plan.price * 12

        # Free plan - activate immediately
        if amount <= 0:
            now = datetime.now(UTC)
            period_end = now + timedelta(
                days=30 if billing_cycle == BillingCycle.MONTHLY else 365
            )

            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle=billing_cycle,
                current_period_start=now,
                current_period_end=period_end,
            )
            session.add(subscription)
            self._update_user_quota(session, user_id, plan_id)
            session.commit()

            logger.info(f"Free subscription activated: {subscription.id}")
            return subscription, None

        # Paid plan - create pending subscription and get authorization URL
        # Delete any existing expired/canceled subscription first
        if existing:
            session.delete(existing)
            session.flush()

        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.PENDING,
            billing_cycle=billing_cycle,
            current_period_start=datetime.now(UTC),
            current_period_end=datetime.now(UTC),  # Will be set after first charge
        )
        session.add(subscription)
        session.commit()

        # Get authorization URL from payment provider
        result = await self.payment_service.get_authorization_url(
            remote_id=str(user_id),
            callback_url=callback_url,
            success_url=success_url,
            error_url=error_url,
        )

        if not result.success:
            logger.error(f"Failed to get authorization URL: {result.error}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Payment provider error: {result.error}",
            )

        logger.info(f"Subscription pending authorization: {subscription.id}")
        return subscription, result.authorization_url

    async def complete_authorization(
        self,
        session: Session,
        user_id: uuid.UUID,
        provider_user_uuid: str,
    ) -> Subscription:
        """
        Complete authorization and charge first payment.

        Called from the callback endpoint after user authorizes on QvaPay.
        """
        subscription = session.exec(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        if subscription.status != SubscriptionStatus.PENDING:
            # Already processed or in different state
            subscription.provider_user_uuid = provider_user_uuid
            session.commit()
            return subscription

        # Save authorization
        subscription.provider_user_uuid = provider_user_uuid
        session.flush()

        # Charge first payment
        plan = subscription.plan
        if subscription.billing_cycle == BillingCycle.MONTHLY:
            amount = plan.price
            period_days = 30
        else:
            amount = plan.price_yearly if plan.price_yearly > 0 else plan.price * 12
            period_days = 365

        now = datetime.now(UTC)
        period_end = now + timedelta(days=period_days)

        # Create payment record
        payment = Payment(
            subscription_id=subscription.id,
            amount=amount,
            currency="USD",
            period_start=now,
            period_end=period_end,
            status=PaymentStatus.PENDING,
            provider=self.payment_service.provider_name,
        )
        session.add(payment)
        session.flush()

        # Charge the user
        charge_result = await self.payment_service.charge_authorized_user(
            user_uuid=provider_user_uuid,
            amount=amount,
            currency="USD",
            description=f"Subscription: {plan.name} ({subscription.billing_cycle.value})",
            remote_id=str(payment.id),
        )

        if charge_result.success:
            payment.status = PaymentStatus.COMPLETED
            payment.provider_transaction_id = charge_result.transaction_id
            payment.paid_at = now

            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = now
            subscription.current_period_end = period_end

            self._update_user_quota(session, subscription.user_id, subscription.plan_id)

            session.commit()
            logger.info(f"Subscription activated: {subscription.id}")
        else:
            payment.status = PaymentStatus.FAILED
            subscription.status = SubscriptionStatus.EXPIRED

            session.commit()
            logger.error(
                f"First charge failed for {subscription.id}: {charge_result.error}"
            )

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Payment failed: {charge_result.error}",
            )

        return subscription

    async def process_renewal(
        self,
        session: Session,
        subscription_id: uuid.UUID,
    ) -> Payment:
        """
        Process automatic subscription renewal.

        Called by the renewal job for subscriptions with authorized payments.
        """
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        if not subscription.provider_user_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No payment authorization",
            )

        if subscription.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription not active",
            )

        if subscription.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELED
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription canceled",
            )

        plan = subscription.plan
        now = subscription.current_period_end

        if subscription.billing_cycle == BillingCycle.MONTHLY:
            amount = plan.price
            period_end = now + timedelta(days=30)
        else:
            amount = plan.price_yearly if plan.price_yearly > 0 else plan.price * 12
            period_end = now + timedelta(days=365)

        # Create payment record
        payment = Payment(
            subscription_id=subscription.id,
            amount=amount,
            currency="USD",
            period_start=now,
            period_end=period_end,
            status=PaymentStatus.PENDING,
            provider=self.payment_service.provider_name,
        )
        session.add(payment)
        session.flush()

        # Charge automatically
        charge_result = await self.payment_service.charge_authorized_user(
            user_uuid=subscription.provider_user_uuid,
            amount=amount,
            currency="USD",
            description=f"Renewal: {plan.name} ({subscription.billing_cycle.value})",
            remote_id=str(payment.id),
        )

        if charge_result.success:
            payment.status = PaymentStatus.COMPLETED
            payment.provider_transaction_id = charge_result.transaction_id
            payment.paid_at = datetime.now(UTC)

            subscription.current_period_start = now
            subscription.current_period_end = period_end

            session.commit()
            logger.info(f"Renewal successful: {subscription_id}")
        else:
            payment.status = PaymentStatus.FAILED
            subscription.status = SubscriptionStatus.PAST_DUE

            session.commit()
            logger.warning(f"Renewal failed: {subscription_id}: {charge_result.error}")

        return payment

    @staticmethod
    def cancel_subscription(
        session: Session,
        subscription_id: uuid.UUID,
        immediate: bool = False,
    ) -> Subscription:
        """Cancel a subscription."""
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        if subscription.status == SubscriptionStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already canceled",
            )

        if immediate:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.now(UTC)
            SubscriptionService._downgrade_to_free_plan(session, subscription.user_id)
            logger.info(f"Subscription canceled: {subscription_id}")
        else:
            subscription.cancel_at_period_end = True
            subscription.canceled_at = datetime.now(UTC)
            logger.info(f"Subscription will cancel at period end: {subscription_id}")

        session.commit()
        return subscription

    @staticmethod
    def expire_subscription(
        session: Session,
        subscription_id: uuid.UUID,
    ) -> Subscription:
        """Expire a subscription after failed renewals."""
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        subscription.status = SubscriptionStatus.EXPIRED
        SubscriptionService._downgrade_to_free_plan(session, subscription.user_id)

        session.commit()
        logger.info(f"Subscription expired: {subscription_id}")

        return subscription

    @staticmethod
    def _update_user_quota(
        session: Session, user_id: uuid.UUID, plan_id: uuid.UUID
    ) -> None:
        """Update user's quota to a new plan."""
        quota = session.exec(
            select(UserQuota).where(UserQuota.user_id == user_id)
        ).first()

        if quota:
            quota.plan_id = plan_id
            quota.sms_sent_this_month = 0
            quota.last_reset_date = datetime.now(UTC)
        else:
            quota = UserQuota(
                user_id=user_id,
                plan_id=plan_id,
                sms_sent_this_month=0,
                devices_registered=0,
            )
            session.add(quota)

    @staticmethod
    def _downgrade_to_free_plan(session: Session, user_id: uuid.UUID) -> None:
        """Downgrade user to free plan."""
        free_plan = session.exec(
            select(UserPlan).where(UserPlan.name.ilike("%free%"))  # type: ignore
        ).first()

        if free_plan:
            quota = session.exec(
                select(UserQuota).where(UserQuota.user_id == user_id)
            ).first()
            if quota:
                quota.plan_id = free_plan.id


# Singleton
_subscription_service: SubscriptionService | None = None


def get_subscription_service() -> SubscriptionService:
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
