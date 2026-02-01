# Plan de Implementación: Sistema de Suscripciones con QvaPay

## Contexto

### Estado Actual del Código (Ender)

| Componente | Estado | Detalles |
|------------|--------|----------|
| Modelos de Plan (`UserPlan`) | ✅ Existe | name, max_sms_per_month, max_devices, price |
| Tracking de Cuotas (`UserQuota`) | ✅ Existe | SMS enviados, dispositivos registrados, fecha reset |
| Enforcement de límites | ✅ Existe | HTTP 429 cuando se excede cuota |
| Asignación de planes | ⚠️ Parcial | Solo superusers pueden cambiar planes |
| QStash Service | ✅ Existe | Cola de mensajes con `enqueue()`, verificación de firma |
| Procesamiento de pagos | ❌ No existe | Sin integración con pasarelas |
| Estados de suscripción | ❌ No existe | Sin active/canceled/paused |
| Historial de pagos | ❌ No existe | Sin facturas ni transacciones |
| Webhooks de pago | ❌ No existe | Sin notificaciones de QvaPay |

### API de QvaPay Disponible

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/info` | GET | Autenticación/info de app |
| `/balance` | GET | Consultar saldo |
| `/create_invoice` | GET | Crear factura de pago único |
| `/transactions` | GET | Listar transacciones |
| `/transaction/{uuid}` | GET | Detalle de transacción |

**⚠️ QvaPay NO tiene soporte nativo para:**
- Suscripciones recurrentes
- Cobros automáticos programados
- Gestión de planes de membresía

---

## Plan de Implementación

### Fase 1: Modelos de Base de Datos

#### 1.1 Nuevo modelo: `Subscription`

```python
# backend/app/models.py

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"        # Esperando primer pago
    PAST_DUE = "past_due"      # Pago vencido
    CANCELED = "canceled"
    EXPIRED = "expired"

class Subscription(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True, ondelete="CASCADE")
    plan_id: uuid.UUID = Field(foreign_key="userplan.id", ondelete="RESTRICT")
    status: SubscriptionStatus = Field(default=SubscriptionStatus.PENDING)

    # Ciclo de facturación
    billing_cycle: str = Field(default="monthly")  # monthly, yearly
    current_period_start: datetime
    current_period_end: datetime

    # Control de cancelación
    cancel_at_period_end: bool = Field(default=False)
    canceled_at: datetime | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Relaciones
    user: "User" = Relationship(back_populates="subscription")
    plan: "UserPlan" = Relationship()
    payments: list["Payment"] = Relationship(back_populates="subscription")
```

#### 1.2 Nuevo modelo: `Payment`

```python
class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class Payment(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    subscription_id: uuid.UUID = Field(foreign_key="subscription.id", ondelete="CASCADE")

    # Provider-agnostic fields (works with QvaPay, Tropipay, etc.)
    provider: str = Field(max_length=50)  # "qvapay", "tropipay", etc.
    provider_transaction_id: str | None = Field(unique=True, index=True)
    provider_invoice_id: str | None = Field(index=True)
    provider_invoice_url: str | None

    # Payment details
    amount: float
    currency: str = Field(default="USD", max_length=10)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)

    # Billing period covered by this payment
    period_start: datetime
    period_end: datetime

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    paid_at: datetime | None = None

    # Relationship
    subscription: "Subscription" = Relationship(back_populates="payments")
```

#### 1.3 Actualizar `UserPlan`

```python
class UserPlan(UserPlanBase, table=True):
    # ... campos existentes ...

    # Nuevos campos
    billing_period: str = Field(default="monthly")  # monthly, yearly
    price_monthly: float = Field(default=0.0)
    price_yearly: float = Field(default=0.0)
    is_public: bool = Field(default=True)  # Visible en lista de planes
```

---

### Fase 2: Abstracción de Proveedores de Pago

Siguiendo el patrón ya establecido en `backend/app/services/email/`, creamos una arquitectura de providers que permite agregar nuevos proveedores de pago (QvaPay, Tropipay, etc.) fácilmente.

#### 2.1 Estructura de archivos

```
backend/app/services/payment/
├── __init__.py
├── base.py                 # Clases abstractas e interfaces
├── payment_service.py      # Servicio principal (factory)
├── qvapay_provider.py      # Implementación QvaPay
└── tropipay_provider.py    # Implementación Tropipay (futuro)
```

#### 2.2 Clases base (`backend/app/services/payment/base.py`)

```python
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
    metadata: dict = field(default_factory=dict)


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
    raw_response: dict | None = None


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
    raw_response: dict | None = None


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
```

#### 2.3 Implementación QvaPay (`backend/app/services/payment/qvapay_provider.py`)

```python
"""
QvaPay payment provider implementation.

QvaPay API docs: https://qvapay.com/docs
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

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        """Create a QvaPay invoice."""
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
                        "app_id": self.app_id,
                        "app_secret": self.app_secret,
                        "amount": request.amount,
                        "description": request.description,
                        "remote_id": request.remote_id,
                    },
                    timeout=30.0,
                )
                data = response.json()

                if response.status_code == 200 and data.get("url"):
                    return InvoiceResult(
                        success=True,
                        invoice_id=data.get("transation_uuid"),  # QvaPay typo
                        payment_url=data.get("url"),
                        raw_response=data,
                    )
                else:
                    return InvoiceResult(
                        success=False,
                        error=data.get("error", "Unknown error"),
                        raw_response=data,
                    )

        except Exception as e:
            logger.error(f"QvaPay create_invoice error: {e}")
            return InvoiceResult(success=False, error=str(e))

    async def get_transaction(self, transaction_id: str) -> TransactionInfo | None:
        """Get transaction details from QvaPay."""
        if not self.is_configured():
            return None

        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/transaction/{transaction_id}",
                    params={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return None

                data = response.json()

                # Map QvaPay status to our status
                status_map = {
                    "paid": TransactionStatus.COMPLETED,
                    "pending": TransactionStatus.PENDING,
                    "cancelled": TransactionStatus.FAILED,
                }

                return TransactionInfo(
                    transaction_id=data.get("uuid", transaction_id),
                    remote_id=data.get("remote_id"),
                    status=status_map.get(
                        data.get("status"), TransactionStatus.PENDING
                    ),
                    amount=float(data.get("amount", 0)),
                    currency="USD",
                    paid_at=data.get("paid_at"),
                    raw_response=data,
                )

        except Exception as e:
            logger.error(f"QvaPay get_transaction error: {e}")
            return None

    async def verify_payment(self, remote_id: str) -> PaymentVerification:
        """Verify if payment was completed by searching transactions."""
        if not self.is_configured():
            return PaymentVerification(is_paid=False, error="QvaPay not configured")

        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/transactions",
                    params={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return PaymentVerification(
                        is_paid=False,
                        error="Failed to fetch transactions",
                    )

                data = response.json()
                transactions = data.get("data", [])

                for tx in transactions:
                    if tx.get("remote_id") == remote_id and tx.get("status") == "paid":
                        return PaymentVerification(
                            is_paid=True,
                            transaction_id=tx.get("uuid"),
                            paid_at=tx.get("paid_at"),
                        )

                return PaymentVerification(is_paid=False)

        except Exception as e:
            logger.error(f"QvaPay verify_payment error: {e}")
            return PaymentVerification(is_paid=False, error=str(e))

    async def get_balance(self) -> float | None:
        """Get QvaPay account balance."""
        if not self.is_configured():
            return None

        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/balance",
                    params={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("balance", 0))
                return None

        except Exception as e:
            logger.error(f"QvaPay get_balance error: {e}")
            return None
```

#### 2.4 Implementación Tropipay (placeholder) (`backend/app/services/payment/tropipay_provider.py`)

```python
"""
Tropipay payment provider implementation.

Tropipay API docs: https://tropipay.com/docs
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
        environment: str = "sandbox",
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
        """Get OAuth access token from Tropipay."""
        # TODO: Implementar autenticación OAuth2
        # POST /access/token
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def create_invoice(self, request: InvoiceRequest) -> InvoiceResult:
        """Create a Tropipay payment link."""
        # TODO: Implementar creación de payment link
        # POST /paymentcards
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def get_transaction(self, transaction_id: str) -> TransactionInfo | None:
        """Get transaction details from Tropipay."""
        # TODO: Implementar consulta de transacción
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def verify_payment(self, remote_id: str) -> PaymentVerification:
        """Verify if payment was completed."""
        # TODO: Implementar verificación
        raise NotImplementedError("Tropipay provider not yet implemented")

    async def get_balance(self) -> float | None:
        """Get Tropipay account balance."""
        # TODO: Implementar consulta de balance
        raise NotImplementedError("Tropipay provider not yet implemented")

    def supports_webhooks(self) -> bool:
        return True  # Tropipay soporta webhooks
```

#### 2.5 Servicio principal (`backend/app/services/payment/payment_service.py`)

```python
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
            return TropipayProvider()
        else:
            # Default to QvaPay
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
        metadata: dict | None = None,
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
```

#### 2.6 Exports (`backend/app/services/payment/__init__.py`)

```python
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
```

---

### Fase 3: Servicio de Suscripciones

Ahora usa `PaymentService` genérico en lugar de un proveedor específico.

#### 3.1 `backend/app/services/subscription_service.py`

```python
"""
Subscription management service.

Handles subscription lifecycle: creation, payments, renewals, and cancellations.
Uses the abstract PaymentService for provider-agnostic payment processing.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
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
        billing_cycle: str = "monthly",
    ) -> tuple[Subscription, Payment, str | None]:
        """
        Create a subscription and generate the first invoice.

        Args:
            session: Database session
            user_id: User ID
            plan_id: Plan to subscribe to
            billing_cycle: "monthly" or "yearly"

        Returns:
            Tuple of (subscription, payment, payment_url)

        Raises:
            HTTPException: If plan not found or payment creation fails
        """
        plan = session.get(UserPlan, plan_id)
        if not plan:
            raise HTTPException(404, "Plan no encontrado")

        # Calculate billing period
        now = datetime.now(UTC)
        if billing_cycle == "monthly":
            period_end = now + timedelta(days=30)
            amount = plan.price_monthly
        else:
            period_end = now + timedelta(days=365)
            amount = plan.price_yearly

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
            provider=self.payment_service.provider_name,  # Track which provider
        )
        session.add(payment)
        session.flush()

        # Generate invoice via payment provider
        invoice_result = await self.payment_service.create_invoice(
            amount=amount,
            currency="USD",
            description=f"Suscripción {plan.name} - {billing_cycle}",
            remote_id=str(payment.id),
        )

        if not invoice_result.success:
            logger.error(f"Failed to create invoice: {invoice_result.error}")
            # Rollback the subscription and payment
            session.rollback()
            raise HTTPException(
                502,
                f"Error al crear factura: {invoice_result.error}",
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

        Raises:
            HTTPException: If payment not found
        """
        payment = session.get(Payment, payment_id)
        if not payment:
            raise HTTPException(404, "Pago no encontrado")

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
        quota = session.exec(
            select(UserQuota).where(UserQuota.user_id == subscription.user_id)
        ).first()

        if quota:
            quota.plan_id = subscription.plan_id
            # Reset counters on plan change
            if was_pending:
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
            raise HTTPException(404, "Pago no encontrado")

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
        if not subscription or subscription.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(400, "Suscripción no válida para renovación")

        if subscription.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELED
            session.commit()
            raise HTTPException(400, "Suscripción cancelada")

        plan = subscription.plan
        now = subscription.current_period_end

        if subscription.billing_cycle == "monthly":
            period_end = now + timedelta(days=30)
            amount = plan.price_monthly
        else:
            period_end = now + timedelta(days=365)
            amount = plan.price_yearly

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
            description=f"Renovación {plan.name} - {subscription.billing_cycle}",
            remote_id=str(payment.id),
        )

        if not invoice_result.success:
            logger.error(f"Failed to create renewal invoice: {invoice_result.error}")
            session.rollback()
            raise HTTPException(502, f"Error al crear factura: {invoice_result.error}")

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
            raise HTTPException(404, "Suscripción no encontrada")

        if immediate:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.now(UTC)

            # Downgrade to Free plan
            free_plan = session.exec(
                select(UserPlan).where(UserPlan.name == "Free")
            ).first()

            if free_plan:
                quota = session.exec(
                    select(UserQuota).where(UserQuota.user_id == subscription.user_id)
                ).first()
                if quota:
                    quota.plan_id = free_plan.id

            logger.info(f"Subscription cancelled immediately: {subscription_id}")
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
            raise HTTPException(404, "Suscripción no encontrada")

        subscription.status = SubscriptionStatus.EXPIRED

        # Downgrade to Free plan
        free_plan = session.exec(
            select(UserPlan).where(UserPlan.name == "Free")
        ).first()

        if free_plan:
            quota = session.exec(
                select(UserQuota).where(UserQuota.user_id == subscription.user_id)
            ).first()
            if quota:
                quota.plan_id = free_plan.id

        session.commit()

        logger.info(f"Subscription expired: {subscription_id}")

        return subscription


# Singleton instance
_subscription_service: SubscriptionService | None = None


def get_subscription_service() -> SubscriptionService:
    """Get the subscription service singleton."""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
```

---

### Fase 4: Endpoints API

#### 4.1 `backend/app/api/routes/subscriptions.py`

```python
router = APIRouter()

@router.post("/subscribe")
async def create_subscription(
    plan_id: uuid.UUID,
    billing_cycle: str = "monthly",
    session: SessionDep,
    current_user: CurrentUser,
) -> SubscriptionCreateResponse:
    """Iniciar proceso de suscripción - retorna URL de pago QvaPay"""
    subscription, payment, payment_url = await SubscriptionService.create_subscription(
        session=session,
        user_id=current_user.id,
        plan_id=plan_id,
        billing_cycle=billing_cycle,
    )
    return SubscriptionCreateResponse(
        subscription_id=subscription.id,
        payment_id=payment.id,
        payment_url=payment_url,
        amount=payment.amount,
        message="Completa el pago en QvaPay para activar tu suscripción"
    )

@router.post("/verify-payment/{payment_id}")
async def verify_payment(
    payment_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> SubscriptionPublic:
    """Verificar manualmente si el pago fue completado"""
    payment = session.get(Payment, payment_id)
    if not payment or payment.subscription.user_id != current_user.id:
        raise HTTPException(404, "Pago no encontrado")

    # Verificar en QvaPay
    qvapay = QvaPayService()
    is_paid = await qvapay.verify_payment(str(payment_id))

    if not is_paid:
        raise HTTPException(402, "Pago no completado aún")

    # Procesar confirmación
    subscription = await SubscriptionService.process_payment_confirmation(
        session=session,
        payment_id=payment_id,
        qvapay_transaction_id="verified_manually"
    )
    return subscription

@router.get("/my-subscription")
async def get_my_subscription(
    session: SessionDep,
    current_user: CurrentUser,
) -> SubscriptionPublic | None:
    """Obtener suscripción activa del usuario"""
    subscription = session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).first()
    return subscription

@router.post("/cancel")
async def cancel_subscription(
    immediate: bool = False,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    """Cancelar suscripción"""
    subscription = session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).first()
    if not subscription:
        raise HTTPException(404, "No tienes suscripción activa")

    SubscriptionService.cancel_subscription(
        session=session,
        subscription_id=subscription.id,
        immediate=immediate
    )

    if immediate:
        return Message(message="Suscripción cancelada inmediatamente")
    return Message(message="Suscripción se cancelará al final del período actual")

@router.get("/payments")
async def get_payment_history(
    session: SessionDep,
    current_user: CurrentUser,
) -> PaymentsPublic:
    """Obtener historial de pagos"""
    subscription = session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).first()
    if not subscription:
        return PaymentsPublic(data=[], count=0)

    payments = session.exec(
        select(Payment)
        .where(Payment.subscription_id == subscription.id)
        .order_by(Payment.created_at.desc())
    ).all()
    return PaymentsPublic(data=payments, count=len(payments))
```

---

### Fase 5: Webhook de QvaPay (Opcional)

Si QvaPay soporta webhooks (verificar con ellos):

```python
@router.post("/webhook/qvapay")
async def qvapay_webhook(
    request: Request,
    session: SessionDep,
):
    """Recibir notificaciones de pago de QvaPay"""
    # Verificar firma del webhook (si QvaPay lo soporta)
    payload = await request.json()

    remote_id = payload.get("remote_id")
    transaction_id = payload.get("transaction_id")
    status = payload.get("status")

    if status == "paid" and remote_id:
        try:
            payment_id = uuid.UUID(remote_id)
            await SubscriptionService.process_payment_confirmation(
                session=session,
                payment_id=payment_id,
                qvapay_transaction_id=transaction_id
            )
        except Exception as e:
            logger.error(f"Error procesando webhook: {e}")

    return {"status": "ok"}
```

---

### Fase 6: Tareas Programadas con Upstash QStash Schedules

Ya tienes `QStashService` implementado en tu proyecto. Usaremos **QStash Schedules** para las renovaciones automáticas.

> Documentación: https://upstash.com/docs/qstash/features/schedules

#### 6.1 Extender QStashService (`backend/app/services/qstash_service.py`)

```python
# Agregar métodos para schedules

class QStashService:
    # ... código existente ...

    # ID fijo para el schedule de renovaciones (permite upsert)
    RENEWAL_SCHEDULE_ID = "subscription-renewal-daily"

    @classmethod
    def create_renewal_schedule(cls) -> str | None:
        """
        Crear/actualizar schedule para verificar renovaciones diariamente.
        Usa scheduleId fijo para permitir actualizaciones idempotentes.
        """
        if not cls._client:
            logger.error("QStash not initialized - cannot create schedule")
            return None

        webhook_url = f"{settings.SERVER_BASE_URL}/api/v1/subscriptions/jobs/check-renewals"

        try:
            # Ejecutar diariamente a las 08:00 UTC
            response = cls._client.schedule.create(
                destination=webhook_url,
                cron="0 8 * * *",  # 8:00 AM UTC todos los días
                schedule_id=cls.RENEWAL_SCHEDULE_ID,
                retries=3,
            )
            logger.info(f"Renewal schedule created/updated: {response.schedule_id}")
            return response.schedule_id

        except Exception as e:
            logger.error(f"Failed to create renewal schedule: {e}")
            return None

    @classmethod
    def delete_renewal_schedule(cls) -> bool:
        """Eliminar schedule de renovaciones."""
        if not cls._client:
            return False

        try:
            cls._client.schedule.delete(cls.RENEWAL_SCHEDULE_ID)
            logger.info("Renewal schedule deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete renewal schedule: {e}")
            return False

    @classmethod
    def get_renewal_schedule(cls) -> dict | None:
        """Obtener info del schedule de renovaciones."""
        if not cls._client:
            return None

        try:
            return cls._client.schedule.get(cls.RENEWAL_SCHEDULE_ID)
        except Exception:
            return None
```

#### 6.2 Endpoint para el Job (`backend/app/api/routes/subscriptions.py`)

```python
@router.post("/jobs/check-renewals")
async def check_renewals_job(
    request: Request,
    session: SessionDep,
):
    """
    Endpoint llamado por QStash Schedule diariamente.
    Verifica firma de QStash para seguridad.
    """
    # Verificar que la request viene de QStash
    signature = request.headers.get("Upstash-Signature", "")
    body = await request.body()
    url = str(request.url)

    if not QStashService.verify_signature(body, signature, url):
        raise HTTPException(401, "Invalid QStash signature")

    now = datetime.now(UTC)
    results = {
        "checked_at": now.isoformat(),
        "renewals_generated": 0,
        "subscriptions_expired": 0,
        "errors": [],
    }

    # 1. Generar facturas para suscripciones que vencen pronto
    threshold = now + timedelta(days=settings.RENEWAL_REMINDER_DAYS)
    expiring = session.exec(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end <= threshold,
            Subscription.current_period_end > now,
            Subscription.cancel_at_period_end == False,
        )
    ).all()

    for subscription in expiring:
        # Verificar si ya tiene pago pendiente
        pending_payment = session.exec(
            select(Payment).where(
                Payment.subscription_id == subscription.id,
                Payment.status == PaymentStatus.PENDING,
            )
        ).first()

        if not pending_payment:
            try:
                payment, url = await SubscriptionService.generate_renewal_invoice(
                    session, subscription.id
                )
                # Encolar email de recordatorio via QStash
                QStashService.enqueue(
                    endpoint="/api/v1/subscriptions/jobs/send-renewal-email",
                    payload={
                        "user_id": str(subscription.user_id),
                        "payment_id": str(payment.id),
                        "payment_url": url,
                    },
                    deduplication_id=f"renewal-email-{payment.id}",
                )
                results["renewals_generated"] += 1
            except Exception as e:
                results["errors"].append(f"subscription {subscription.id}: {str(e)}")

    # 2. Expirar suscripciones con pago vencido (grace period pasado)
    grace_period = timedelta(days=settings.SUBSCRIPTION_GRACE_PERIOD_DAYS)
    expired = session.exec(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.PAST_DUE,
            Subscription.current_period_end < now - grace_period,
        )
    ).all()

    for subscription in expired:
        try:
            SubscriptionService.expire_subscription(session, subscription.id)
            results["subscriptions_expired"] += 1
        except Exception as e:
            results["errors"].append(f"expire {subscription.id}: {str(e)}")

    logger.info(f"Renewal job completed: {results}")
    return results


@router.post("/jobs/send-renewal-email")
async def send_renewal_email_job(
    request: Request,
    session: SessionDep,
):
    """Job para enviar email de renovación (llamado desde QStash queue)."""
    # Verificar firma
    signature = request.headers.get("Upstash-Signature", "")
    body = await request.body()
    url = str(request.url)

    if not QStashService.verify_signature(body, signature, url):
        raise HTTPException(401, "Invalid QStash signature")

    payload = await request.json()
    user_id = uuid.UUID(payload["user_id"])
    payment_url = payload["payment_url"]

    user = session.get(User, user_id)
    if user:
        await send_email(
            email_to=user.email,
            subject="Tu suscripción está por vencer",
            template="renewal_reminder",
            context={
                "user_name": user.full_name or user.email,
                "payment_url": payment_url,
            },
        )

    return {"status": "sent"}
```

#### 6.3 Inicializar Schedule al arrancar la app (`backend/app/main.py`)

```python
@app.on_event("startup")
async def startup_event():
    # ... código existente de QStash ...
    QStashService.initialize()

    # Crear schedule de renovaciones (idempotente)
    if settings.ENVIRONMENT != "local":
        QStashService.create_renewal_schedule()
```

#### 6.4 Endpoint admin para gestionar el schedule

```python
@router.post("/admin/schedules/renewal", dependencies=[Depends(get_current_superuser)])
async def manage_renewal_schedule(
    action: Literal["create", "delete", "status"],
):
    """Gestionar el schedule de renovaciones (solo superuser)."""
    if action == "create":
        schedule_id = QStashService.create_renewal_schedule()
        return {"action": "created", "schedule_id": schedule_id}
    elif action == "delete":
        success = QStashService.delete_renewal_schedule()
        return {"action": "deleted", "success": success}
    else:  # status
        schedule = QStashService.get_renewal_schedule()
        return {"schedule": schedule}
```

---

### Fase 7: Configuración

#### 7.1 Variables de entorno (`backend/app/core/config.py`)

```python
class Settings(BaseSettings):
    # ... campos existentes ...

    # Payment Provider Configuration
    # Options: "qvapay", "tropipay"
    # To add new providers, implement PaymentProvider in app/services/payment/
    PAYMENT_PROVIDER: str = "qvapay"

    # QvaPay credentials
    QVAPAY_APP_ID: str | None = None
    QVAPAY_APP_SECRET: str | None = None

    # Tropipay credentials (for future use)
    TROPIPAY_CLIENT_ID: str | None = None
    TROPIPAY_CLIENT_SECRET: str | None = None
    TROPIPAY_ENVIRONMENT: str = "sandbox"  # "sandbox" or "production"

    # Subscription settings
    SUBSCRIPTION_GRACE_PERIOD_DAYS: int = 3   # Grace period after expiration
    RENEWAL_REMINDER_DAYS: int = 3            # Days before expiration to send reminder

    @computed_field
    @property
    def qvapay_enabled(self) -> bool:
        """Check if QvaPay is configured."""
        return bool(self.QVAPAY_APP_ID and self.QVAPAY_APP_SECRET)

    @computed_field
    @property
    def tropipay_enabled(self) -> bool:
        """Check if Tropipay is configured."""
        return bool(self.TROPIPAY_CLIENT_ID and self.TROPIPAY_CLIENT_SECRET)

    @computed_field
    @property
    def payments_enabled(self) -> bool:
        """Check if any payment provider is configured."""
        provider = self.PAYMENT_PROVIDER.lower()
        if provider == "qvapay":
            return self.qvapay_enabled
        elif provider == "tropipay":
            return self.tropipay_enabled
        return False
```

#### 7.2 Actualizar `.env.example`

```bash
# =============================================================================
# Payment Provider Configuration
# =============================================================================
# Choose your payment provider: qvapay, tropipay
PAYMENT_PROVIDER=qvapay

# QvaPay Configuration (if PAYMENT_PROVIDER=qvapay)
QVAPAY_APP_ID=your_app_id
QVAPAY_APP_SECRET=your_app_secret

# Tropipay Configuration (if PAYMENT_PROVIDER=tropipay)
# TROPIPAY_CLIENT_ID=your_client_id
# TROPIPAY_CLIENT_SECRET=your_client_secret
# TROPIPAY_ENVIRONMENT=sandbox  # or "production"

# =============================================================================
# Subscription Settings
# =============================================================================
SUBSCRIPTION_GRACE_PERIOD_DAYS=3
RENEWAL_REMINDER_DAYS=3
```

---

## Flujo de Usuario

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUJO DE SUSCRIPCIÓN                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Usuario selecciona plan                                     │
│         │                                                       │
│         ▼                                                       │
│  2. POST /subscriptions/subscribe                               │
│         │                                                       │
│         ▼                                                       │
│  3. Se crea Subscription (PENDING) + Payment (PENDING)          │
│         │                                                       │
│         ▼                                                       │
│  4. QvaPay create_invoice → Retorna URL de pago                 │
│         │                                                       │
│         ▼                                                       │
│  5. Frontend redirige a QvaPay                                  │
│         │                                                       │
│         ▼                                                       │
│  6. Usuario paga en QvaPay                                      │
│         │                                                       │
│         ├──────────────────┬────────────────────┐               │
│         ▼                  ▼                    ▼               │
│    [Webhook]         [Polling]          [Verificación          │
│    (si existe)       Frontend            Manual]                │
│         │                  │                    │               │
│         └──────────────────┴────────────────────┘               │
│                            │                                    │
│                            ▼                                    │
│  7. process_payment_confirmation()                              │
│         │                                                       │
│         ▼                                                       │
│  8. Subscription → ACTIVE, UserQuota → nuevo plan               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     FLUJO DE RENOVACIÓN                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. QStash Schedule llama endpoint diariamente (8:00 UTC)       │
│         │                                                       │
│         ▼                                                       │
│  2. Genera factura de renovación en QvaPay                      │
│         │                                                       │
│         ▼                                                       │
│  3. Envía email al usuario con link de pago                     │
│         │                                                       │
│         ▼                                                       │
│  4. Usuario paga → mismo flujo de confirmación                  │
│         │                                                       │
│         ▼                                                       │
│  5. Se extiende current_period_end                              │
│                                                                 │
│  * Si no paga en 3 días: status → EXPIRED, plan → Free          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Resumen de Archivos a Crear/Modificar

### Crear (Payment Providers):
```
backend/app/services/payment/
├── __init__.py                 # Exports públicos
├── base.py                     # PaymentProvider ABC, dataclasses
├── payment_service.py          # Factory service (como email_service.py)
├── qvapay_provider.py          # Implementación QvaPay
└── tropipay_provider.py        # Implementación Tropipay (placeholder)
```

### Crear (Subscriptions):
- `backend/app/services/subscription_service.py` - Lógica de suscripciones
- `backend/app/api/routes/subscriptions.py` - Endpoints REST + jobs
- `backend/app/alembic/versions/xxx_add_subscriptions.py` - Migración DB
- `backend/app/email-templates/src/renewal_reminder.mjml` - Template email

### Modificar:
- `backend/app/models.py` - Agregar Subscription, Payment, SubscriptionStatus, PaymentStatus
- `backend/app/core/config.py` - Variables de payment providers y suscripciones
- `backend/app/api/main.py` - Registrar router de subscriptions
- `backend/app/services/qstash_service.py` - Agregar métodos de schedules
- `backend/app/main.py` - Inicializar schedule en startup
- `frontend/` - Páginas de planes, checkout, historial de pagos

---

## Arquitectura de Providers

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PAYMENT PROVIDER ABSTRACTION                      │
│                    (Similar a Email Providers)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                     PaymentProvider (ABC)                    │   │
│   │  - create_invoice(request) -> InvoiceResult                 │   │
│   │  - get_transaction(id) -> TransactionInfo                   │   │
│   │  - verify_payment(remote_id) -> PaymentVerification         │   │
│   │  - get_balance() -> float                                   │   │
│   │  - is_configured() -> bool                                  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              ▲                                      │
│              ┌───────────────┼───────────────┐                      │
│              │               │               │                      │
│   ┌──────────┴───┐  ┌────────┴────┐  ┌───────┴───────┐             │
│   │ QvaPayProvider│  │TropipayProv│  │ Future Provs  │             │
│   │              │  │             │  │ (Stripe, etc) │             │
│   └──────────────┘  └─────────────┘  └───────────────┘             │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    PaymentService                            │   │
│   │  - Auto-selects provider from PAYMENT_PROVIDER env var      │   │
│   │  - Provides unified API for SubscriptionService             │   │
│   │  - Singleton via get_payment_service()                      │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Arquitectura con QStash

```
┌─────────────────────────────────────────────────────────────────────┐
│                    UPSTASH QSTASH SCHEDULES                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────┐         ┌─────────────────────────────────┐   │
│   │  QStash Cloud   │         │        Tu Backend (Ender)       │   │
│   │                 │         │                                 │   │
│   │  Schedule:      │  HTTP   │  POST /subscriptions/jobs/      │   │
│   │  "0 8 * * *"    │ ──────► │       check-renewals            │   │
│   │  (8 AM UTC)     │         │                                 │   │
│   │                 │         │  1. Busca suscripciones por     │   │
│   │  Verifica firma │         │     vencer (próximos 3 días)    │   │
│   │  automáticamente│         │                                 │   │
│   └─────────────────┘         │  2. Genera facturas via         │   │
│                               │     PaymentService (genérico)   │   │
│   ┌─────────────────┐         │                                 │   │
│   │  QStash Queue   │         │  3. Encola emails via QStash    │   │
│   │  "sms-notif..."│ ◄────── │     Queue (existente)           │   │
│   │                 │         │                                 │   │
│   │  Procesa emails │         │  4. Expira suscripciones        │   │
│   │  de renovación  │         │     vencidas (grace period)     │   │
│   └─────────────────┘         └─────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Consideraciones Importantes

1. **Sin cobro automático**: Ni QvaPay ni Tropipay cobran automáticamente. Cada renovación requiere acción del usuario.

2. **Grace period**: Dar 3 días después del vencimiento antes de degradar el plan.

3. **Emails críticos**: Notificar antes del vencimiento y cuando el pago esté pendiente.

4. **Verificación de pagos**: Implementar tanto webhook (si el provider lo soporta) como verificación manual desde el frontend.

5. **Idempotencia**: Usar `remote_id` (payment.id) para evitar procesar el mismo pago dos veces.

6. **Plan Free como fallback**: Siempre tener un plan gratuito para usuarios que no renueven.

7. **QStash Schedule**:
   - Se crea automáticamente al iniciar la app en producción
   - Usa `schedule_id` fijo para permitir actualizaciones idempotentes
   - La verificación de firma ya está implementada en `QStashService.verify_signature()`

8. **Reutilización de código existente**:
   - `QStashService.enqueue()` para emails de renovación
   - `QStashService.verify_signature()` para validar requests de schedules
   - Sistema de email existente para templates

9. **Agregar nuevos providers**: Seguir el patrón de `backend/app/services/email/`:
   - Crear `new_provider.py` que herede de `PaymentProvider`
   - Implementar todos los métodos abstractos
   - Agregar el tipo en `PaymentProviderType` enum
   - Agregar las credenciales en `Settings`
   - Registrar en `PaymentService._create_provider()`
