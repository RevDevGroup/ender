"""
Subscription management service.

Handles subscription lifecycle: creation, payments, renewals, and cancellations.
Uses the abstract PaymentService for provider-agnostic payment processing.
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
    Service for managing user subscriptions.

    This service:
    - Creates subscriptions with initial payment
    - Processes payment confirmations
    - Generates renewal invoices
    - Handles cancellations and expirations
    """

    def __init__(self, payment_service: PaymentService | None = None):
        """
        Initialize the subscription service.

        Args:
            payment_service: Optional payment service. Uses singleton if not provided.
        """
        self._payment_service = payment_service

    @property
    def payment_service(self) -> PaymentService:
        """Get the payment service."""
        if self._payment_service is None:
            self._payment_service = get_payment_service()
        return self._payment_service

    async def create_subscription(
        self,
        session: Session,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
    ) -> tuple[Subscription, Payment, str | None]:
        """
        Create a subscription and generate the first invoice.

        Args:
            session: Database session
            user_id: User ID
            plan_id: Plan to subscribe to
            billing_cycle: Monthly or yearly billing

        Returns:
            Tuple of (subscription, payment, payment_url)

        Raises:
            HTTPException: If plan not found or payment creation fails
        """
        # Check for existing subscription
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
                detail="This plan is not available for subscription",
            )

        # Calculate billing period and amount
        now = datetime.now(UTC)
        if billing_cycle == BillingCycle.MONTHLY:
            period_end = now + timedelta(days=30)
            amount = plan.price
        else:
            period_end = now + timedelta(days=365)
            amount = plan.price_yearly if plan.price_yearly > 0 else plan.price * 12

        # Free plan doesn't need payment
        if amount <= 0:
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle=billing_cycle,
                current_period_start=now,
                current_period_end=period_end,
            )
            session.add(subscription)

            # Update user quota
            self._update_user_quota(session, user_id, plan_id)
            session.commit()

            logger.info(f"Free subscription created: {subscription.id}")
            return subscription, None, None  # type: ignore

        # Create subscription (pending until first payment)
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.PENDING,
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=period_end,
        )
        session.add(subscription)
        session.flush()

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

        # Generate invoice via payment provider
        invoice_result = await self.payment_service.create_invoice(
            amount=amount,
            currency="USD",
            description=f"Subscription: {plan.name} ({billing_cycle.value})",
            remote_id=str(payment.id),
        )

        if not invoice_result.success:
            logger.error(f"Failed to create invoice: {invoice_result.error}")
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create payment invoice: {invoice_result.error}",
            )

        # Store invoice details
        payment.provider_invoice_id = invoice_result.invoice_id
        payment.provider_invoice_url = invoice_result.payment_url
        session.commit()

        logger.info(
            f"Subscription created: {subscription.id} via {self.payment_service.provider_name}"
        )

        return subscription, payment, invoice_result.payment_url

    async def process_payment_confirmation(
        self,
        session: Session,
        payment_id: uuid.UUID,
        provider_transaction_id: str,
    ) -> Subscription:
        """
        Process payment confirmation (from webhook or manual verification).

        Activates the subscription and updates user quota.

        Args:
            session: Database session
            payment_id: Payment ID
            provider_transaction_id: Transaction ID from payment provider

        Returns:
            Updated subscription
        """
        payment = session.get(Payment, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        if payment.status == PaymentStatus.COMPLETED:
            # Already processed
            return payment.subscription

        # Update payment
        payment.status = PaymentStatus.COMPLETED
        payment.provider_transaction_id = provider_transaction_id
        payment.paid_at = datetime.now(UTC)

        # Activate subscription
        subscription = payment.subscription
        was_pending = subscription.status == SubscriptionStatus.PENDING

        subscription.status = SubscriptionStatus.ACTIVE

        # If this is a renewal, extend the period
        if not was_pending:
            subscription.current_period_start = payment.period_start
            subscription.current_period_end = payment.period_end

        # Update user quota to new plan
        self._update_user_quota(session, subscription.user_id, subscription.plan_id)

        # Reset SMS counter on new subscription
        if was_pending:
            quota = session.exec(
                select(UserQuota).where(UserQuota.user_id == subscription.user_id)
            ).first()
            if quota:
                quota.sms_sent_this_month = 0
                quota.last_reset_date = datetime.now(UTC)

        session.commit()

        logger.info(f"Payment confirmed: {payment_id}, subscription: {subscription.id}")

        return subscription

    async def verify_and_process_payment(
        self,
        session: Session,
        payment_id: uuid.UUID,
    ) -> Subscription | None:
        """
        Verify payment status with provider and process if paid.

        Args:
            session: Database session
            payment_id: Payment ID to verify

        Returns:
            Updated subscription if paid, None otherwise
        """
        payment = session.get(Payment, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        if payment.status == PaymentStatus.COMPLETED:
            return payment.subscription

        # Verify with payment provider
        verification = await self.payment_service.verify_payment(str(payment_id))

        if verification.is_paid:
            return await self.process_payment_confirmation(
                session=session,
                payment_id=payment_id,
                provider_transaction_id=verification.transaction_id or "verified",
            )

        return None

    async def generate_renewal_invoice(
        self,
        session: Session,
        subscription_id: uuid.UUID,
    ) -> tuple[Payment, str | None]:
        """
        Generate renewal invoice for existing subscription.

        Called by the renewal job before subscription expires.

        Args:
            session: Database session
            subscription_id: Subscription to renew

        Returns:
            Tuple of (payment, payment_url)
        """
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        if subscription.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is not active",
            )

        if subscription.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELED
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is scheduled for cancellation",
            )

        plan = subscription.plan
        now = subscription.current_period_end

        if subscription.billing_cycle == BillingCycle.MONTHLY:
            period_end = now + timedelta(days=30)
            amount = plan.price
        else:
            period_end = now + timedelta(days=365)
            amount = plan.price_yearly if plan.price_yearly > 0 else plan.price * 12

        # Create pending payment
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

        # Generate invoice via payment provider
        invoice_result = await self.payment_service.create_invoice(
            amount=amount,
            currency="USD",
            description=f"Renewal: {plan.name} ({subscription.billing_cycle.value})",
            remote_id=str(payment.id),
        )

        if not invoice_result.success:
            logger.error(f"Failed to create renewal invoice: {invoice_result.error}")
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create renewal invoice: {invoice_result.error}",
            )

        payment.provider_invoice_id = invoice_result.invoice_id
        payment.provider_invoice_url = invoice_result.payment_url
        subscription.status = SubscriptionStatus.PAST_DUE

        session.commit()

        logger.info(f"Renewal invoice created for subscription: {subscription_id}")

        return payment, invoice_result.payment_url

    @staticmethod
    def cancel_subscription(
        session: Session,
        subscription_id: uuid.UUID,
        immediate: bool = False,
    ) -> Subscription:
        """
        Cancel a subscription.

        Args:
            session: Database session
            subscription_id: Subscription to cancel
            immediate: If True, cancel now. If False, cancel at period end.

        Returns:
            Updated subscription
        """
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        if subscription.status == SubscriptionStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is already canceled",
            )

        if immediate:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.now(UTC)

            # Downgrade to Free plan
            SubscriptionService._downgrade_to_free_plan(session, subscription.user_id)

            logger.info(f"Subscription canceled immediately: {subscription_id}")
        else:
            subscription.cancel_at_period_end = True
            subscription.canceled_at = datetime.now(UTC)
            logger.info(f"Subscription scheduled for cancellation: {subscription_id}")

        session.commit()
        return subscription

    @staticmethod
    def expire_subscription(
        session: Session,
        subscription_id: uuid.UUID,
    ) -> Subscription:
        """
        Expire a subscription (grace period ended without payment).

        Args:
            session: Database session
            subscription_id: Subscription to expire

        Returns:
            Updated subscription
        """
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        subscription.status = SubscriptionStatus.EXPIRED

        # Downgrade to Free plan
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
        else:
            # Create quota if it doesn't exist
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


# Singleton instance
_subscription_service: SubscriptionService | None = None


def get_subscription_service() -> SubscriptionService:
    """Get the subscription service singleton."""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
