"""
Tropipay payment provider implementation (placeholder).

Tropipay API documentation: https://tpp.stoplight.io/docs/tropipay-api-doc

This is a placeholder implementation. To complete it:
1. Implement OAuth2 authentication flow
2. Implement payment link creation via POST /api/v2/paymentcards
3. Implement transaction verification
4. Add webhook signature verification

Endpoints to implement:
- POST /api/v2/access/token - OAuth2 token
- POST /api/v2/paymentcards - Create payment link
- GET /api/v2/paymentcards/{id} - Get payment card details
- GET /api/v2/movements - List movements/transactions
"""

import logging

from app.core.config import settings

from .base import (
    InvoiceRequest,
    InvoiceResult,
    PaymentProvider,
    PaymentVerification,
    TransactionInfo,
)

logger = logging.getLogger(__name__)


class TropipayProvider(PaymentProvider):
    """
    Tropipay payment provider.

    Configuration (via environment):
        TROPIPAY_CLIENT_ID: Client ID from Tropipay
        TROPIPAY_CLIENT_SECRET: Client secret from Tropipay
        TROPIPAY_ENVIRONMENT: "sandbox" or "production"
    """

    SANDBOX_URL = "https://tropipay-dev.herokuapp.com/api/v2"
    PRODUCTION_URL = "https://www.tropipay.com/api/v2"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        environment: str | None = None,
    ):
        self.client_id = client_id or getattr(settings, "TROPIPAY_CLIENT_ID", None)
        self.client_secret = client_secret or getattr(
            settings, "TROPIPAY_CLIENT_SECRET", None
        )
        self.environment = environment or getattr(
            settings, "TROPIPAY_ENVIRONMENT", "sandbox"
        )
        self._access_token: str | None = None

    @property
    def provider_name(self) -> str:
        return "tropipay"

    @property
    def base_url(self) -> str:
        return (
            self.PRODUCTION_URL
            if self.environment == "production"
            else self.SANDBOX_URL
        )

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _get_access_token(self) -> str | None:
        """
        Get OAuth access token from Tropipay.

        TODO: Implement OAuth2 client credentials flow
        POST /api/v2/access/token
        """
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        """
        Create a Tropipay payment link.

        TODO: Implement payment card creation
        POST /api/v2/paymentcards
        """
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def get_transaction(self, transaction_id: str) -> TransactionInfo | None:
        """
        Get transaction details from Tropipay.

        TODO: Implement transaction lookup
        GET /api/v2/paymentcards/{id}
        """
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def verify_payment(self, remote_id: str) -> PaymentVerification:
        """
        Verify if payment was completed.

        TODO: Implement payment verification
        """
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def get_balance(self) -> float | None:
        """
        Get Tropipay account balance.

        TODO: Implement balance lookup
        """
        raise NotImplementedError("Tropipay provider not yet implemented")

    def supports_webhooks(self) -> bool:
        """Tropipay supports webhooks for payment notifications."""
        return True

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Tropipay webhook signature.

        TODO: Implement signature verification based on Tropipay docs
        """
        raise NotImplementedError("Tropipay webhook verification not yet implemented")
