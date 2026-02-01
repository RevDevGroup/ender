"""
Base payment provider interface.

This module defines the abstract base class that all payment providers must implement.
To add a new provider, create a new class that inherits from PaymentProvider and
implements all abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class InvoiceStatus(str, Enum):
    """Status of a payment invoice."""

    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TransactionStatus(str, Enum):
    """Status of a payment transaction."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class InvoiceRequest:
    """
    Request to create a payment invoice.

    Attributes:
        amount: Amount to charge
        currency: Currency code (USD, EUR, etc.)
        description: Description shown to user
        remote_id: Internal ID for tracking (e.g., payment.id)
        webhook_url: URL to receive payment notifications (optional)
        success_url: URL to redirect user after successful payment (optional)
        error_url: URL to redirect user if payment fails/cancelled (optional)
        metadata: Additional provider-specific data
    """

    amount: float
    currency: str
    description: str
    remote_id: str
    webhook_url: str | None = None
    success_url: str | None = None
    error_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class InvoiceResult:
    """
    Result of creating an invoice.

    Attributes:
        success: Whether the invoice was created successfully
        invoice_id: Provider-specific invoice ID
        payment_url: URL where user completes payment
        expires_at: When the invoice expires (optional)
        error: Error message if failed
        raw_response: Raw provider response (for debugging)
    """

    success: bool
    invoice_id: str | None = None
    payment_url: str | None = None
    expires_at: str | None = None
    error: str | None = None
    raw_response: dict[str, object] | None = None


@dataclass
class TransactionInfo:
    """
    Information about a payment transaction.

    Attributes:
        transaction_id: Provider-specific transaction ID
        remote_id: Our internal reference ID
        status: Current transaction status
        amount: Transaction amount
        currency: Currency code
        paid_at: When payment was completed (if paid)
        raw_response: Raw provider response
    """

    transaction_id: str
    remote_id: str | None
    status: TransactionStatus
    amount: float
    currency: str
    paid_at: str | None = None
    raw_response: dict[str, object] | None = None


@dataclass
class PaymentVerification:
    """
    Result of verifying a payment.

    Attributes:
        is_paid: Whether the payment was completed
        transaction_id: Provider transaction ID (if found)
        paid_at: When payment was made (if paid)
        error: Error message if verification failed
    """

    is_paid: bool
    transaction_id: str | None = None
    paid_at: str | None = None
    error: str | None = None


@dataclass
class AuthorizationRequest:
    """
    Request to get payment authorization from a user.

    Attributes:
        remote_id: Internal ID for tracking (e.g., user.id or subscription.id)
        callback_url: URL called by provider after authorization (server-to-server)
        success_url: URL where user is redirected after successful authorization
        error_url: URL where user is redirected if authorization fails or is cancelled
        metadata: Additional provider-specific data
    """

    remote_id: str
    callback_url: str
    success_url: str
    error_url: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class AuthorizationResult:
    """
    Result of requesting payment authorization.

    Attributes:
        success: Whether the authorization URL was created successfully
        authorization_url: URL where user authorizes payments
        expires_at: When the authorization URL expires (optional)
        error: Error message if failed
        raw_response: Raw provider response (for debugging)
    """

    success: bool
    authorization_url: str | None = None
    expires_at: str | None = None
    error: str | None = None
    raw_response: dict[str, object] | None = None


@dataclass
class ChargeRequest:
    """
    Request to charge an authorized user.

    Attributes:
        user_uuid: Provider-specific user UUID (obtained after authorization)
        amount: Amount to charge
        currency: Currency code (USD, EUR, etc.)
        description: Description shown to user
        remote_id: Internal ID for tracking (e.g., payment.id)
        metadata: Additional provider-specific data
    """

    user_uuid: str
    amount: float
    currency: str
    description: str
    remote_id: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ChargeResult:
    """
    Result of charging an authorized user.

    Attributes:
        success: Whether the charge was successful
        transaction_id: Provider-specific transaction ID
        amount: Amount charged
        error: Error message if failed
        raw_response: Raw provider response (for debugging)
    """

    success: bool
    transaction_id: str | None = None
    amount: float | None = None
    error: str | None = None
    raw_response: dict[str, object] | None = None


class WebhookEventType(str, Enum):
    """Types of webhook events from payment providers."""

    PAYMENT_COMPLETED = "payment_completed"
    AUTHORIZATION_COMPLETED = "authorization_completed"
    PAYMENT_FAILED = "payment_failed"


@dataclass
class WebhookEvent:
    """
    Parsed webhook event from a payment provider.

    Attributes:
        event_type: Type of the event
        transaction_id: Provider transaction ID (for payments)
        remote_id: Our internal reference ID (payment.id or user.id)
        user_uuid: Provider's user UUID (for authorization events)
        amount: Transaction amount (if applicable)
        raw_payload: Original webhook payload
    """

    event_type: WebhookEventType
    remote_id: str
    transaction_id: str | None = None
    user_uuid: str | None = None
    amount: float | None = None
    raw_payload: dict[str, object] = field(default_factory=dict)


class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.

    To implement a new provider:
    1. Create a new class that inherits from PaymentProvider
    2. Implement all abstract methods
    3. Register the provider in PaymentService

    Example:
        class TropipayProvider(PaymentProvider):
            def __init__(self, client_id: str, client_secret: str):
                self.client_id = client_id
                self.client_secret = client_secret

            async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
                # Implementation here
                pass
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'qvapay', 'tropipay')."""
        pass

    @abstractmethod
    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        """
        Create a payment invoice/link.

        Args:
            request: Invoice creation request

        Returns:
            InvoiceResult with payment URL or error
        """
        pass

    @abstractmethod
    async def get_transaction(self, transaction_id: str) -> TransactionInfo | None:
        """
        Get transaction details by provider transaction ID.

        Args:
            transaction_id: Provider-specific transaction ID

        Returns:
            TransactionInfo or None if not found
        """
        pass

    @abstractmethod
    async def verify_payment(self, remote_id: str) -> PaymentVerification:
        """
        Verify if a payment was completed by our internal reference ID.

        Args:
            remote_id: Our internal reference (e.g., payment.id)

        Returns:
            PaymentVerification with payment status
        """
        pass

    @abstractmethod
    async def get_balance(self) -> float | None:
        """
        Get current account balance.

        Returns:
            Balance amount or None if unavailable
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.

        Returns:
            True if all required credentials are set
        """
        pass

    def supports_webhooks(self) -> bool:
        """
        Check if the provider supports webhooks.

        Returns:
            True if webhooks are supported (default: False)
        """
        return False

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature from provider.

        Args:
            payload: Raw webhook payload
            signature: Signature header value

        Returns:
            True if signature is valid (default: True if no verification)
        """
        return True

    def supports_authorized_payments(self) -> bool:
        """
        Check if the provider supports authorized/recurring payments.

        Returns:
            True if authorized payments are supported (default: False)
        """
        return False

    async def get_authorization_url(
        self, request: "AuthorizationRequest"
    ) -> "AuthorizationResult":
        """
        Get a URL where the user can authorize recurring payments.

        Args:
            request: Authorization request with callback URL

        Returns:
            AuthorizationResult with authorization URL or error

        Raises:
            NotImplementedError: If provider doesn't support authorized payments
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support authorized payments"
        )

    async def charge_authorized_user(self, request: "ChargeRequest") -> "ChargeResult":
        """
        Charge a user who has previously authorized payments.

        Args:
            request: Charge request with user UUID and amount

        Returns:
            ChargeResult with transaction ID or error

        Raises:
            NotImplementedError: If provider doesn't support authorized payments
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support authorized payments"
        )

    def parse_webhook(
        self, payload: dict[str, object], headers: dict[str, str]
    ) -> WebhookEvent | None:
        """
        Parse a webhook payload from this provider.

        Each provider implements their own parsing logic based on their
        webhook format.

        Args:
            payload: Webhook payload (parsed JSON or query params)
            headers: HTTP headers from the webhook request

        Returns:
            WebhookEvent if successfully parsed, None if invalid/unrecognized
        """
        raise NotImplementedError(
            f"{self.provider_name} does not implement webhook parsing"
        )
