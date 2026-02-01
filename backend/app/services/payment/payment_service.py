"""
Payment service with provider abstraction.

This module provides a unified interface for payment operations, regardless of the
underlying provider (QvaPay, Tropipay, etc.).

To switch providers, change the PAYMENT_PROVIDER environment variable.
"""

import logging
from enum import Enum
from functools import lru_cache

from app.core.config import settings

from .base import (
    AuthorizationRequest,
    AuthorizationResult,
    ChargeRequest,
    ChargeResult,
    InvoiceRequest,
    InvoiceResult,
    PaymentProvider,
    PaymentVerification,
    TransactionInfo,
)
from .qvapay_provider import QvaPayProvider
from .tropipay_provider import TropipayProvider

logger = logging.getLogger(__name__)


class PaymentProviderType(str, Enum):
    """Supported payment provider types."""

    QVAPAY = "qvapay"
    TROPIPAY = "tropipay"
    # Future providers:
    # STRIPE = "stripe"
    # PAYPAL = "paypal"


class PaymentService:
    """
    Main payment service that abstracts provider selection.

    This service:
    - Automatically selects the configured provider
    - Provides a unified API for payment operations
    - Handles provider initialization and configuration

    Usage:
        service = PaymentService()
        result = await service.create_invoice(
            amount=10.00,
            currency="USD",
            description="Pro Plan - Monthly",
            remote_id=str(payment.id),
        )

    Configuration (via environment):
        PAYMENT_PROVIDER: Provider to use (qvapay, tropipay)

        For QvaPay:
            QVAPAY_APP_ID, QVAPAY_APP_SECRET

        For Tropipay:
            TROPIPAY_CLIENT_ID, TROPIPAY_CLIENT_SECRET, TROPIPAY_ENVIRONMENT
    """

    def __init__(self, provider: PaymentProvider | None = None):
        """
        Initialize the payment service.

        Args:
            provider: Optional provider instance. If not provided,
                     will be auto-detected from configuration.
        """
        self._provider = provider

    @property
    def provider(self) -> PaymentProvider:
        """Get the payment provider, initializing if needed."""
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    @property
    def provider_name(self) -> str:
        """Get the active provider name."""
        return self.provider.provider_name

    def _create_provider(self) -> PaymentProvider:
        """Create the appropriate provider based on configuration."""
        provider_type = getattr(settings, "PAYMENT_PROVIDER", "qvapay").lower()

        if provider_type == PaymentProviderType.TROPIPAY:
            logger.info("Using Tropipay payment provider")
            return TropipayProvider()
        else:
            # Default to QvaPay
            logger.info("Using QvaPay payment provider")
            return QvaPayProvider()

    def is_configured(self) -> bool:
        """Check if payment service is properly configured."""
        return self.provider.is_configured()

    async def create_invoice(
        self,
        *,
        amount: float,
        currency: str = "USD",
        description: str,
        remote_id: str,
        metadata: dict[str, str] | None = None,
    ) -> InvoiceResult:
        """
        Create a payment invoice.

        Args:
            amount: Amount to charge
            currency: Currency code (default: USD)
            description: Description shown to user
            remote_id: Internal reference ID (payment.id)
            metadata: Additional data (optional)

        Returns:
            InvoiceResult with payment URL or error
        """
        if not self.is_configured():
            logger.warning("Payment service is not configured")
            return InvoiceResult(
                success=False,
                error="Payment service is not configured",
            )

        request = InvoiceRequest(
            amount=amount,
            currency=currency,
            description=description,
            remote_id=remote_id,
            metadata=metadata or {},
        )

        result = await self.provider.create_invoice(request)

        if result.success:
            logger.info(
                f"Invoice created via {self.provider_name}: {result.invoice_id}"
            )
        else:
            logger.error(
                f"Failed to create invoice via {self.provider_name}: {result.error}"
            )

        return result

    async def get_transaction(self, transaction_id: str) -> TransactionInfo | None:
        """
        Get transaction details.

        Args:
            transaction_id: Provider-specific transaction ID

        Returns:
            TransactionInfo or None
        """
        return await self.provider.get_transaction(transaction_id)

    async def verify_payment(self, remote_id: str) -> PaymentVerification:
        """
        Verify if a payment was completed.

        Args:
            remote_id: Internal reference ID (payment.id)

        Returns:
            PaymentVerification with status
        """
        return await self.provider.verify_payment(remote_id)

    async def get_balance(self) -> float | None:
        """
        Get provider account balance.

        Returns:
            Balance amount or None
        """
        return await self.provider.get_balance()

    def supports_webhooks(self) -> bool:
        """Check if the current provider supports webhooks."""
        return self.provider.supports_webhooks()

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from current provider."""
        return self.provider.verify_webhook_signature(payload, signature)

    # ==================== Authorized Payments ====================

    def supports_authorized_payments(self) -> bool:
        """
        Check if the current provider supports authorized/recurring payments.

        Returns:
            True if authorized payments are supported
        """
        return self.provider.supports_authorized_payments()

    async def get_authorization_url(
        self,
        *,
        remote_id: str,
        callback_url: str,
        success_url: str,
        error_url: str,
        metadata: dict[str, str] | None = None,
    ) -> AuthorizationResult:
        """
        Get a URL where the user can authorize recurring payments.

        After the user authorizes, they will be redirected to success_url.
        The callback_url is called server-to-server by the provider.

        Args:
            remote_id: Internal reference ID (user.id or subscription.id)
            callback_url: URL called by provider after authorization (server-to-server)
            success_url: URL where user is redirected after successful authorization
            error_url: URL where user is redirected if authorization fails or is cancelled
            metadata: Additional data (optional)

        Returns:
            AuthorizationResult with authorization URL or error
        """
        if not self.supports_authorized_payments():
            return AuthorizationResult(
                success=False,
                error=f"{self.provider_name} does not support authorized payments",
            )

        if not self.is_configured():
            return AuthorizationResult(
                success=False,
                error="Payment service is not configured",
            )

        request = AuthorizationRequest(
            remote_id=remote_id,
            callback_url=callback_url,
            success_url=success_url,
            error_url=error_url,
            metadata=metadata or {},
        )

        result = await self.provider.get_authorization_url(request)

        if result.success:
            logger.info(
                f"Authorization URL created via {self.provider_name} "
                f"for remote_id={remote_id}"
            )
        else:
            logger.error(
                f"Failed to create authorization URL via {self.provider_name}: "
                f"{result.error}"
            )

        return result

    async def charge_authorized_user(
        self,
        *,
        user_uuid: str,
        amount: float,
        currency: str = "USD",
        description: str,
        remote_id: str,
        metadata: dict[str, str] | None = None,
    ) -> ChargeResult:
        """
        Charge a user who has previously authorized payments.

        The user must have completed the authorization flow and you must
        have their user_uuid from the callback.

        Args:
            user_uuid: Provider-specific user UUID (from authorization callback)
            amount: Amount to charge
            currency: Currency code (default: USD)
            description: Description shown to user
            remote_id: Internal reference ID (payment.id)
            metadata: Additional data (optional)

        Returns:
            ChargeResult with transaction ID or error
        """
        if not self.supports_authorized_payments():
            return ChargeResult(
                success=False,
                error=f"{self.provider_name} does not support authorized payments",
            )

        if not self.is_configured():
            return ChargeResult(
                success=False,
                error="Payment service is not configured",
            )

        request = ChargeRequest(
            user_uuid=user_uuid,
            amount=amount,
            currency=currency,
            description=description,
            remote_id=remote_id,
            metadata=metadata or {},
        )

        result = await self.provider.charge_authorized_user(request)

        if result.success:
            logger.info(
                f"Charge successful via {self.provider_name}: "
                f"transaction={result.transaction_id}, amount={amount}"
            )
        else:
            logger.error(f"Failed to charge via {self.provider_name}: {result.error}")

        return result


# Singleton instance
_payment_service: PaymentService | None = None


@lru_cache
def get_payment_service() -> PaymentService:
    """
    Get the payment service singleton.

    Returns:
        PaymentService instance
    """
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService()
    return _payment_service
