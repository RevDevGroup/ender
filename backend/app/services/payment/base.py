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
        metadata: Additional provider-specific data
    """

    amount: float
    currency: str
    description: str
    remote_id: str
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
