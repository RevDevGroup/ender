"""
QvaPay payment provider implementation.

QvaPay API v2 (Merchants) documentation:
https://documenter.getpostman.com/view/8765260/TzzHnDGw#merchants

Endpoints:
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
    WebhookEvent,
    WebhookEventType,
)

logger = logging.getLogger(__name__)


class QvaPayProvider(PaymentProvider):
    """
    QvaPay payment provider using API v2 (Merchants).

    Configuration (via environment):
        QVAPAY_APP_ID: Application ID from QvaPay dashboard
        QVAPAY_APP_SECRET: Application secret from QvaPay dashboard
    """

    BASE_URL = "https://api.qvapay.com/v2"
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

    def _get_headers(self) -> dict[str, str]:
        """Get authentication headers for API v2 requests."""
        return {
            "app-id": self.app_id or "",
            "app-secret": self.app_secret or "",
            "Content-Type": "application/json",
        }

    def supports_authorized_payments(self) -> bool:
        """QvaPay supports authorized/recurring payments."""
        return True

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        """Create a payment invoice."""
        if not self.is_configured():
            return InvoiceResult(success=False, error="QvaPay is not configured")

        try:
            payload: dict[str, object] = {
                "amount": request.amount,
                "description": request.description,
                "remote_id": request.remote_id,
            }

            # Add optional webhook URL for payment notifications
            if request.webhook_url:
                payload["webhook"] = request.webhook_url

            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/create_invoice",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                data = response.json()

                if response.status_code == 200 and data.get("url"):
                    return InvoiceResult(
                        success=True,
                        invoice_id=data.get("transaction_uuid")
                        or data.get("transation_uuid")
                        or data.get("uuid"),
                        payment_url=data.get("url"),
                        raw_response=data,
                    )

                error_msg = data.get("error") or data.get("message") or "Unknown error"
                logger.error(f"QvaPay create_invoice failed: {error_msg}")
                return InvoiceResult(success=False, error=error_msg, raw_response=data)

        except Exception as e:
            logger.exception(f"QvaPay create_invoice error: {e}")
            return InvoiceResult(success=False, error=str(e))

    async def get_transaction(self, transaction_id: str) -> TransactionInfo | None:
        """Get transaction details."""
        if not self.is_configured():
            return None

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/transactions/{transaction_id}",
                    headers=self._get_headers(),
                    timeout=self.DEFAULT_TIMEOUT,
                )

                if response.status_code != 200:
                    return None

                data = response.json()
                status_map = {
                    "paid": TransactionStatus.COMPLETED,
                    "pending": TransactionStatus.PENDING,
                    "cancelled": TransactionStatus.FAILED,
                }

                return TransactionInfo(
                    transaction_id=data.get("uuid", transaction_id),
                    remote_id=data.get("remote_id"),
                    status=status_map.get(
                        data.get("status", "").lower(), TransactionStatus.PENDING
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
        """Verify if payment was completed."""
        if not self.is_configured():
            return PaymentVerification(is_paid=False, error="QvaPay not configured")

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/transactions",
                    headers=self._get_headers(),
                    timeout=self.DEFAULT_TIMEOUT,
                )

                if response.status_code != 200:
                    return PaymentVerification(is_paid=False, error="Failed to fetch")

                data = response.json()
                for tx in data.get("data", []):
                    if tx.get("remote_id") == remote_id:
                        if tx.get("status", "").lower() == "paid":
                            return PaymentVerification(
                                is_paid=True,
                                transaction_id=tx.get("uuid"),
                                paid_at=tx.get("paid_at"),
                            )
                        return PaymentVerification(is_paid=False)

                return PaymentVerification(is_paid=False)

        except Exception as e:
            logger.exception(f"QvaPay verify_payment error: {e}")
            return PaymentVerification(is_paid=False, error=str(e))

    async def get_balance(self) -> float | None:
        """Get account balance."""
        if not self.is_configured():
            return None

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/balance",
                    headers=self._get_headers(),
                    timeout=self.DEFAULT_TIMEOUT,
                )

                if response.status_code == 200:
                    return float(response.json().get("balance", 0))
                return None

        except Exception as e:
            logger.exception(f"QvaPay get_balance error: {e}")
            return None

    async def get_authorization_url(
        self, request: AuthorizationRequest
    ) -> AuthorizationResult:
        """Get URL for user to authorize recurring payments."""
        if not self.is_configured():
            return AuthorizationResult(success=False, error="QvaPay is not configured")

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/authorize_payments",
                    headers=self._get_headers(),
                    json={
                        "remote_id": request.remote_id,
                        "callback": request.callback_url,
                        "success": request.success_url,
                        "error": request.error_url,
                    },
                    timeout=self.DEFAULT_TIMEOUT,
                )
                data = response.json()

                if response.status_code == 200:
                    auth_url = data.get("url") or data.get("authorization_url")
                    if auth_url:
                        return AuthorizationResult(
                            success=True,
                            authorization_url=auth_url,
                            raw_response=data,
                        )
                    return AuthorizationResult(
                        success=False,
                        error="No authorization URL in response",
                        raw_response=data,
                    )

                error_msg = data.get("error") or data.get("message") or "Unknown error"
                logger.error(f"QvaPay authorize_payments failed: {error_msg}")
                return AuthorizationResult(
                    success=False, error=error_msg, raw_response=data
                )

        except Exception as e:
            logger.exception(f"QvaPay authorize_payments error: {e}")
            return AuthorizationResult(success=False, error=str(e))

    async def charge_authorized_user(self, request: ChargeRequest) -> ChargeResult:
        """Charge a user who has authorized payments."""
        if not self.is_configured():
            return ChargeResult(success=False, error="QvaPay is not configured")

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/charge",
                    headers=self._get_headers(),
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
                    transaction_id = (
                        data.get("transaction_uuid")
                        or data.get("transation_uuid")
                        or data.get("uuid")
                    )
                    return ChargeResult(
                        success=True,
                        transaction_id=transaction_id,
                        amount=request.amount,
                        raw_response=data,
                    )

                error_msg = data.get("error") or data.get("message") or "Unknown error"
                logger.error(f"QvaPay charge failed: {error_msg}")
                return ChargeResult(success=False, error=error_msg, raw_response=data)

        except Exception as e:
            logger.exception(f"QvaPay charge error: {e}")
            return ChargeResult(success=False, error=str(e))

    def parse_webhook(
        self, payload: dict[str, object], headers: dict[str, str]
    ) -> WebhookEvent | None:
        """
        Parse QvaPay webhook payload.

        QvaPay sends different payloads for different events:
        - authorize_payments callback: GET with ?user_uuid=xxx&remote_id=xxx
        - invoice webhook: POST with {transaction_uuid, remote_id, status, amount, ...}
        """
        # Authorization callback (from authorize_payments)
        # Comes as query params: user_uuid and remote_id
        if "user_uuid" in payload and "remote_id" in payload:
            return WebhookEvent(
                event_type=WebhookEventType.AUTHORIZATION_COMPLETED,
                remote_id=str(payload["remote_id"]),
                user_uuid=str(payload["user_uuid"]),
                raw_payload=payload,
            )

        # Invoice payment webhook
        # Comes as JSON with transaction_uuid when payment is completed
        transaction_uuid = payload.get("transaction_uuid") or payload.get(
            "transation_uuid"
        )
        if transaction_uuid:
            remote_id = payload.get("remote_id")
            if not remote_id:
                logger.warning("QvaPay webhook missing remote_id")
                return None

            amount = None
            if "amount" in payload:
                try:
                    amount = float(str(payload["amount"]))
                except (ValueError, TypeError):
                    pass

            return WebhookEvent(
                event_type=WebhookEventType.PAYMENT_COMPLETED,
                remote_id=str(remote_id),
                transaction_id=str(transaction_uuid),
                amount=amount,
                raw_payload=payload,
            )

        logger.warning(f"Unrecognized QvaPay webhook payload: {payload}")
        return None
