"""
Subscription management service.

Handles subscription lifecycle with both invoice and automatic payments.
Supports:
- Invoice payments: User pays manually via invoice each period
- Authorized payments: User authorizes once, then automatic charges
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import (
    BillingCycle,
    Payment,
    PaymentMethod,
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
    Service for managing user subscriptions.

    Supports two payment methods:
    1. Invoice (default): User pays manually via invoice
       - Create invoice → User pays → Webhook activates subscription
    2. Authorized: User authorizes recurring payments
       - Get auth URL → User authorizes → Callback charges first payment
       - Renewals are charged automatically
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
        payment_method: PaymentMethod,
        webhook_url: str,
        success_url: str,
        error_url: str,
    ) -> tuple[Subscription, str | None]:
        """
        Start subscription process.

        Args:
            session: Database session
            user_id: User ID
            plan_id: Plan ID to subscribe to
            billing_cycle: Monthly or yearly
            payment_method: Invoice (manual) or Authorized (automatic)
            webhook_url: URL for payment provider callbacks
            success_url: URL to redirect user after success
            error_url: URL to redirect user on error/cancel

        Returns:
            (subscription, redirect_url)
            - Free plans: (subscription, None) - activated immediately
            - Invoice: (subscription, payment_url) - user pays at this URL
            - Authorized: (subscription, authorization_url) - user authorizes here
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

        # Calculate amount and period
        if billing_cycle == BillingCycle.MONTHLY:
            amount = plan.price
            period_days = 30
        else:
            amount = plan.price_yearly if plan.price_yearly > 0 else plan.price * 12
            period_days = 365

        # Free plan - activate immediately
        if amount <= 0:
            now = datetime.now(UTC)
            period_end = now + timedelta(days=period_days)

            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle=billing_cycle,
                payment_method=payment_method,
                current_period_start=now,
                current_period_end=period_end,
            )
            session.add(subscription)
            self._update_user_quota(session, user_id, plan_id)
            session.commit()

            logger.info(f"Free subscription activated: {subscription.id}")
            return subscription, None

        # Delete any existing expired/canceled subscription first
        if existing:
            session.delete(existing)
            session.flush()

        # Create pending subscription
        now = datetime.now(UTC)
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.PENDING,
            billing_cycle=billing_cycle,
            payment_method=payment_method,
            current_period_start=now,
            current_period_end=now,  # Will be set after payment
        )
        session.add(subscription)
        session.flush()

        if payment_method == PaymentMethod.INVOICE:
            # Create invoice for manual payment
            return await self._start_invoice_subscription(
                session=session,
                subscription=subscription,
                plan=plan,
                amount=amount,
                period_days=period_days,
                webhook_url=webhook_url,
            )
        else:
            # Get authorization URL for automatic payments
            return await self._start_authorized_subscription(
                session=session,
                subscription=subscription,
                user_id=user_id,
                webhook_url=webhook_url,
                success_url=success_url,
                error_url=error_url,
            )

    async def _start_invoice_subscription(
        self,
        session: Session,
        subscription: Subscription,
        plan: UserPlan,
        amount: float,
        period_days: int,
        webhook_url: str,
    ) -> tuple[Subscription, str]:
        """Create invoice for manual payment."""
        now = datetime.now(UTC)
        period_end = now + timedelta(days=period_days)

        # Create pending payment record
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

        # Create invoice with webhook
        result = await self.payment_service.create_invoice(
            amount=amount,
            currency="USD",
            description=f"Subscription: {plan.name} ({subscription.billing_cycle.value})",
            remote_id=str(payment.id),
            webhook_url=webhook_url,
        )

        if not result.success:
            logger.error(f"Failed to create invoice: {result.error}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Payment provider error: {result.error}",
            )

        if not result.payment_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment provider did not return payment URL",
            )

        # Save invoice details
        payment.provider_invoice_id = result.invoice_id
        payment.provider_invoice_url = result.payment_url
        session.commit()

        logger.info(
            f"Invoice created for subscription {subscription.id}: {result.invoice_id}"
        )
        return subscription, result.payment_url

    async def _start_authorized_subscription(
        self,
        session: Session,
        subscription: Subscription,
        user_id: uuid.UUID,
        webhook_url: str,
        success_url: str,
        error_url: str,
    ) -> tuple[Subscription, str]:
        """Get authorization URL for automatic payments."""
        session.commit()

        result = await self.payment_service.get_authorization_url(
            remote_id=str(user_id),
            callback_url=webhook_url,
            success_url=success_url,
            error_url=error_url,
        )

        if not result.success or not result.authorization_url:
            logger.error(f"Failed to get authorization URL: {result.error}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Payment provider error: {result.error}",
            )

        logger.info(f"Subscription pending authorization: {subscription.id}")
        return subscription, result.authorization_url

    async def complete_invoice_payment(
        self,
        session: Session,
        payment_id: uuid.UUID,
        transaction_id: str,
    ) -> Subscription:
        """
        Complete subscription when invoice is paid.

        Called from the webhook endpoint when payment provider notifies
        that an invoice has been paid.

        Args:
            session: Database session
            payment_id: Our internal payment ID (passed as remote_id to provider)
            transaction_id: Provider's transaction ID

        Returns:
            Updated subscription
        """
        payment = session.get(Payment, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        # Check if already processed
        if payment.status == PaymentStatus.COMPLETED:
            logger.info(f"Payment {payment_id} already completed, skipping")
            return payment.subscription

        subscription = payment.subscription

        # Update payment
        payment.status = PaymentStatus.COMPLETED
        payment.provider_transaction_id = transaction_id
        payment.paid_at = datetime.now(UTC)

        # Activate subscription if pending
        if subscription.status == SubscriptionStatus.PENDING:
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = payment.period_start
            subscription.current_period_end = payment.period_end

            self._update_user_quota(session, subscription.user_id, subscription.plan_id)

            logger.info(f"Subscription activated via invoice: {subscription.id}")
        elif subscription.status == SubscriptionStatus.PAST_DUE:
            # Renewal payment received
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = payment.period_start
            subscription.current_period_end = payment.period_end

            logger.info(f"Subscription renewed via invoice: {subscription.id}")
        else:
            logger.info(
                f"Payment {payment_id} completed for subscription "
                f"in status {subscription.status}"
            )

        session.commit()
        return subscription

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
