"""
Payment provider abstraction layer.

This module provides a unified interface for payment processing, supporting
multiple providers (QvaPay, Tropipay, etc.) through a common API.

Usage:
    from app.services.payment import get_payment_service

    service = get_payment_service()
    result = await service.create_invoice(
        amount=10.00,
        description="Pro Plan",
        remote_id=str(payment_id),
    )

To add a new provider:
    1. Create a new class inheriting from PaymentProvider
    2. Implement all abstract methods
    3. Add to PaymentProviderType enum
    4. Register in PaymentService._create_provider()
"""

from .base import (
    InvoiceRequest,
    InvoiceResult,
    InvoiceStatus,
    PaymentProvider,
    PaymentVerification,
    TransactionInfo,
    TransactionStatus,
)
from .payment_service import PaymentProviderType, PaymentService, get_payment_service

__all__ = [
    # Base classes
    "PaymentProvider",
    "InvoiceRequest",
    "InvoiceResult",
    "InvoiceStatus",
    "TransactionInfo",
    "TransactionStatus",
    "PaymentVerification",
    # Service
    "PaymentService",
    "PaymentProviderType",
    "get_payment_service",
]
