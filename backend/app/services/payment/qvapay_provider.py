"""
QvaPay payment provider implementation.

QvaPay API documentation: https://documenter.getpostman.com/view/8765260/TzzHnDGw

Endpoints used:
- GET /info - Authentication/app info
- GET /balance - Account balance
- GET /create_invoice - Create payment invoice
- GET /transactions - List transactions
- GET /transaction/{uuid} - Get transaction details
"""

import logging

from httpx import AsyncClient

from app.core.config import settings

from .base import (
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
    """

    BASE_URL = "https://qvapay.com/api/v1"
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
        """Get authentication parameters for API requests."""
        return {
            "app_id": self.app_id or "",
            "app_secret": self.app_secret or "",
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
