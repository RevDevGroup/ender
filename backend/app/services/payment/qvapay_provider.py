"""
QvaPay payment provider implementation.

QvaPay API documentation: https://documenter.getpostman.com/view/8765260/TzzHnDGw

API v1 Endpoints:
- GET /info - Authentication/app info
- GET /balance - Account balance
- GET /create_invoice - Create payment invoice
- GET /transactions - List transactions
- GET /transaction/{uuid} - Get transaction details

API v2 Endpoints (Merchants - Authorized Payments):
- POST /v2/info - App info
- POST /v2/balance - Account balance
- POST /v2/create_invoice - Create payment invoice
- POST /v2/transactions - List transactions
- POST /v2/transactions/{uuid} - Get transaction status
- POST /v2/authorize_payments - Get authorization URL for recurring payments
- POST /v2/charge - Charge user with authorized token
"""

import logging

from httpx import AsyncClient

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
    TransactionStatus,
)

logger = logging.getLogger(__name__)


class QvaPayProvider(PaymentProvider):
    """
    QvaPay payment provider.

    Configuration (via environment):
        QVAPAY_APP_ID: Application ID from QvaPay dashboard
        QVAPAY_APP_SECRET: Application secret from QvaPay dashboard

    Supports:
        - Invoice-based payments (manual user payment)
        - Authorized/recurring payments (automatic charges)
    """

    BASE_URL = "https://qvapay.com/api/v1"
    BASE_URL_V2 = "https://api.qvapay.com/v2"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
    ):
        self.app_id = app_id or getattr(settings, "QVAPAY_APP_ID", None)
        self.app_secret = app_secret or getattr(settings, "QVAPAY_APP_SECRET", None)

    @property
    def provider_name(self) -> str:
        return "qvapay"

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def _get_auth_params(self) -> dict[str, str]:
        """Get authentication parameters for API v1 requests (query params)."""
        return {
            "app_id": self.app_id or "",
            "app_secret": self.app_secret or "",
        }

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API v2 requests."""
        return {
            "app-id": self.app_id or "",
            "app-secret": self.app_secret or "",
            "Content-Type": "application/json",
        }

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        """
        Create a QvaPay invoice.

        QvaPay create_invoice endpoint returns:
        - url: Payment URL for the user
        - transation_uuid: Transaction UUID (note: typo in QvaPay API)
        - signed_url: Signed URL with 30min expiry (if signed=1)
        """
        if not self.is_configured():
            return InvoiceResult(
                success=False,
                error="QvaPay is not configured",
            )

        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/create_invoice",
                    params={
                        **self._get_auth_params(),
                        "amount": request.amount,
                        "description": request.description,
                        "remote_id": request.remote_id,
                    },
                    timeout=self.DEFAULT_TIMEOUT,
                )
                data = response.json()

                if response.status_code == 200 and data.get("url"):
                    return InvoiceResult(
                        success=True,
                        # Note: QvaPay has a typo "transation_uuid" instead of "transaction_uuid"
                        invoice_id=data.get("transation_uuid") or data.get("uuid"),
                        payment_url=data.get("url"),
                        raw_response=data,
                    )
                else:
                    error_msg = (
                        data.get("error") or data.get("message") or "Unknown error"
                    )
                    logger.error(f"QvaPay create_invoice failed: {error_msg}")
                    return InvoiceResult(
                        success=False,
                        error=error_msg,
                        raw_response=data,
                    )

        except Exception as e:
            logger.exception(f"QvaPay create_invoice error: {e}")
            return InvoiceResult(success=False, error=str(e))

    async def get_transaction(self, transaction_id: str) -> TransactionInfo | None:
        """
        Get transaction details from QvaPay.

        Transaction status values from QvaPay:
        - pending: Waiting for payment
        - paid: Payment completed
        - cancelled: Payment cancelled
        """
        if not self.is_configured():
            return None

        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/transaction/{transaction_id}",
                    params=self._get_auth_params(),
                    timeout=self.DEFAULT_TIMEOUT,
                )

                if response.status_code != 200:
                    logger.warning(
                        f"QvaPay get_transaction failed: status={response.status_code}"
                    )
                    return None

                data = response.json()

                # Map QvaPay status to our TransactionStatus
                status_map = {
                    "paid": TransactionStatus.COMPLETED,
                    "pending": TransactionStatus.PENDING,
                    "cancelled": TransactionStatus.FAILED,
                }

                return TransactionInfo(
                    transaction_id=data.get("uuid", transaction_id),
                    remote_id=data.get("remote_id"),
                    status=status_map.get(
                        data.get("status", "").lower(),
                        TransactionStatus.PENDING,
                    ),
                    amount=float(data.get("amount", 0)),
                    currency="USD",
                    paid_at=data.get("paid_at"),
                    raw_response=data,
                )

        except Exception as e:
            logger.exception(f"QvaPay get_transaction error: {e}")
            return None

    async def verify_payment(self, remote_id: str) -> PaymentVerification:
        """
        Verify if payment was completed by searching transactions.

        QvaPay doesn't have a direct endpoint to query by remote_id,
        so we fetch recent transactions and search for the matching one.
        """
        if not self.is_configured():
            return PaymentVerification(is_paid=False, error="QvaPay not configured")

        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/transactions",
                    params=self._get_auth_params(),
                    timeout=self.DEFAULT_TIMEOUT,
                )

                if response.status_code != 200:
                    return PaymentVerification(
                        is_paid=False,
                        error=f"Failed to fetch transactions: status={response.status_code}",
                    )

                data = response.json()
                transactions = data.get("data", [])

                # Search for transaction with matching remote_id
                for tx in transactions:
                    if tx.get("remote_id") == remote_id:
                        status = tx.get("status", "").lower()
                        if status == "paid":
                            return PaymentVerification(
                                is_paid=True,
                                transaction_id=tx.get("uuid"),
                                paid_at=tx.get("paid_at"),
                            )
                        # Found but not paid yet
                        return PaymentVerification(is_paid=False)

                # Not found in transactions list
                return PaymentVerification(is_paid=False)

        except Exception as e:
            logger.exception(f"QvaPay verify_payment error: {e}")
            return PaymentVerification(is_paid=False, error=str(e))

    async def get_balance(self) -> float | None:
        """Get QvaPay account balance."""
        if not self.is_configured():
            return None

        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/balance",
                    params=self._get_auth_params(),
                    timeout=self.DEFAULT_TIMEOUT,
                )

                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("balance", 0))

                logger.warning(
                    f"QvaPay get_balance failed: status={response.status_code}"
                )
                return None

        except Exception as e:
            logger.exception(f"QvaPay get_balance error: {e}")
            return None

    # ==================== Authorized Payments (API v2) ====================

    def supports_authorized_payments(self) -> bool:
        """QvaPay supports authorized/recurring payments via API v2."""
        return True

    async def get_authorization_url(
        self, request: AuthorizationRequest
    ) -> AuthorizationResult:
        """
        Get a URL where the user can authorize recurring payments.

        Uses QvaPay API v2 endpoint: POST /v2/authorize_payments

        The user will be redirected to this URL to authorize your app
        to charge their account. After authorization, they are redirected
        to your callback_url with the user_uuid in the response.

        Args:
            request: Authorization request with callback URL

        Returns:
            AuthorizationResult with authorization URL
        """
        if not self.is_configured():
            return AuthorizationResult(
                success=False,
                error="QvaPay is not configured",
            )

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL_V2}/authorize_payments",
                    headers=self._get_auth_headers(),
                    json={
                        "remote_id": request.remote_id,
                        "callback": request.callback_url,
                    },
                    timeout=self.DEFAULT_TIMEOUT,
                )
                data = response.json()

                if response.status_code == 200:
                    # QvaPay returns a URL where user authorizes payments
                    auth_url = data.get("url") or data.get("authorization_url")
                    if auth_url:
                        return AuthorizationResult(
                            success=True,
                            authorization_url=auth_url,
                            raw_response=data,
                        )
                    else:
                        return AuthorizationResult(
                            success=False,
                            error="No authorization URL in response",
                            raw_response=data,
                        )
                else:
                    error_msg = (
                        data.get("error") or data.get("message") or "Unknown error"
                    )
                    logger.error(f"QvaPay authorize_payments failed: {error_msg}")
                    return AuthorizationResult(
                        success=False,
                        error=error_msg,
                        raw_response=data,
                    )

        except Exception as e:
            logger.exception(f"QvaPay authorize_payments error: {e}")
            return AuthorizationResult(success=False, error=str(e))

    async def charge_authorized_user(self, request: ChargeRequest) -> ChargeResult:
        """
        Charge a user who has previously authorized payments.

        Uses QvaPay API v2 endpoint: POST /v2/charge

        The user must have previously authorized payments via get_authorization_url.
        The charge is processed automatically without user intervention.

        Args:
            request: Charge request with user UUID and amount

        Returns:
            ChargeResult with transaction ID or error
        """
        if not self.is_configured():
            return ChargeResult(
                success=False,
                error="QvaPay is not configured",
            )

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL_V2}/charge",
                    headers=self._get_auth_headers(),
                    json={
                        "amount": request.amount,
                        "user_uuid": request.user_uuid,
                        "description": request.description,
                        "remote_id": request.remote_id,
                    },
                    timeout=self.DEFAULT_TIMEOUT,
                )
                data = response.json()

                if response.status_code == 200:
                    # Successful charge
                    transaction_id = (
                        data.get("transaction_uuid")
                        or data.get("transation_uuid")  # QvaPay typo
                        or data.get("uuid")
                    )
                    return ChargeResult(
                        success=True,
                        transaction_id=transaction_id,
                        amount=request.amount,
                        raw_response=data,
                    )
                else:
                    error_msg = (
                        data.get("error") or data.get("message") or "Unknown error"
                    )
                    logger.error(f"QvaPay charge failed: {error_msg}")
                    return ChargeResult(
                        success=False,
                        error=error_msg,
                        raw_response=data,
                    )

        except Exception as e:
            logger.exception(f"QvaPay charge error: {e}")
            return ChargeResult(success=False, error=str(e))
