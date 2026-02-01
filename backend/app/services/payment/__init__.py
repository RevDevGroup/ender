"""
Payment provider abstraction layer.

This module provides a unified interface for payment processing, supporting
multiple providers (QvaPay, Tropipay, etc.) through a common API.

Usage:
    from app.services.payment import get_payment_service

    # Invoice-based payment (manual)
    service = get_payment_service()
    result = await service.create_invoice(
        amount=10.00,
        description="Pro Plan",
        remote_id=str(payment_id),
    )

    # Authorized payment (automatic/recurring)
    if service.supports_authorized_payments():
        auth_result = await service.get_authorization_url(
            remote_id=str(user_id),
            callback_url="https://myapp.com/callback",
        )
        # User authorizes at auth_result.authorization_url
        # Then charge automatically:
        charge_result = await service.charge_authorized_user(
            user_uuid="user-uuid-from-callback",
            amount=10.00,
            description="Monthly subscription",
            remote_id=str(payment_id),
        )

To add a new provider:
    1. Create a new class inheriting from PaymentProvider
    2. Implement all abstract methods
    3. Add to PaymentProviderType enum
    4. Register in PaymentService._create_provider()
"""

from .base import (
    AuthorizationRequest,
    AuthorizationResult,
    ChargeRequest,
    ChargeResult,
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
    # Authorized payments
    "AuthorizationRequest",
    "AuthorizationResult",
    "ChargeRequest",
    "ChargeResult",
    # Service
    "PaymentService",
    "PaymentProviderType",
    "get_payment_service",
]
