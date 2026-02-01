import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# Subscription and Payment Enums
class SubscriptionStatus(str, Enum):
    """Status of a user subscription."""

    PENDING = "pending"  # Waiting for first payment
    ACTIVE = "active"  # Subscription is active
    PAST_DUE = "past_due"  # Payment overdue, in grace period
    CANCELED = "canceled"  # User canceled
    EXPIRED = "expired"  # Grace period ended without payment


class PaymentStatus(str, Enum):
    """Status of a payment transaction."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class BillingCycle(str, Enum):
    """Billing cycle options."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class PaymentMethod(str, Enum):
    """Payment method for subscriptions."""

    INVOICE = "invoice"  # Manual payment via invoice each period
    AUTHORIZED = "authorized"  # Automatic payments via authorized token


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    email_verified: bool = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserPlanBase(SQLModel):
    name: str = Field(unique=True, index=True, max_length=100)
    max_sms_per_month: int = Field(default=0)
    max_devices: int = Field(default=0)
    price: float = Field(default=0.0)


class UserPlanUpdate(SQLModel):
    """Schema for updating a plan."""

    name: str | None = Field(default=None, max_length=100)
    max_sms_per_month: int | None = None
    max_devices: int | None = None
    price: float | None = None
    price_yearly: float | None = None
    is_public: bool | None = None


class UserPlan(UserPlanBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Additional pricing fields for subscriptions
    price_yearly: float = Field(default=0.0)  # Yearly price (usually discounted)
    is_public: bool = Field(default=True)  # Whether plan is visible to users
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    quotas: list["UserQuota"] = Relationship(back_populates="plan")
    subscriptions: list["Subscription"] = Relationship(back_populates="plan")


# Subscription Models
class SubscriptionBase(SQLModel):
    """Base subscription fields."""

    billing_cycle: BillingCycle = Field(default=BillingCycle.MONTHLY)
    status: SubscriptionStatus = Field(default=SubscriptionStatus.PENDING)
    payment_method: PaymentMethod = Field(default=PaymentMethod.INVOICE)
    cancel_at_period_end: bool = Field(default=False)


class Subscription(SubscriptionBase, table=True):
    """
    User subscription to a plan.

    Tracks the subscription lifecycle including billing periods,
    cancellation state, and payment history.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", unique=True, nullable=False, ondelete="CASCADE"
    )
    plan_id: uuid.UUID = Field(
        foreign_key="userplan.id", nullable=False, ondelete="RESTRICT"
    )

    # Billing period
    current_period_start: datetime = Field(default_factory=lambda: datetime.now(UTC))
    current_period_end: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Authorized payments - stores the user's UUID from payment provider
    # This is obtained when user authorizes recurring payments
    provider_user_uuid: str | None = Field(default=None, max_length=255)

    # Cancellation tracking
    canceled_at: datetime | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    # Relationships
    user: "User" = Relationship(back_populates="subscription")
    plan: UserPlan = Relationship(back_populates="subscriptions")
    payments: list["Payment"] = Relationship(
        back_populates="subscription", cascade_delete=True
    )


class SubscriptionCreate(SQLModel):
    """Schema for creating a subscription."""

    plan_id: uuid.UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class SubscriptionPublic(SubscriptionBase):
    """Public subscription response."""

    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: uuid.UUID
    current_period_start: datetime
    current_period_end: datetime
    canceled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    has_authorized_payments: bool = False  # Computed field


class SubscriptionWithPlan(SubscriptionPublic):
    """Subscription with plan details."""

    plan: "UserPlanPublic"


# Payment Models
class PaymentBase(SQLModel):
    """Base payment fields."""

    amount: float
    currency: str = Field(default="USD", max_length=10)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)


class Payment(PaymentBase, table=True):
    """
    Payment record for a subscription.

    Tracks individual payments including provider details
    and the billing period covered.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    subscription_id: uuid.UUID = Field(
        foreign_key="subscription.id", nullable=False, ondelete="CASCADE"
    )

    # Payment provider info (provider-agnostic)
    provider: str = Field(max_length=50)  # "qvapay", "tropipay", etc.
    provider_transaction_id: str | None = Field(
        default=None, unique=True, index=True, max_length=255
    )
    provider_invoice_id: str | None = Field(default=None, index=True, max_length=255)
    provider_invoice_url: str | None = Field(default=None, max_length=500)

    # Billing period covered by this payment
    period_start: datetime
    period_end: datetime

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    paid_at: datetime | None = Field(default=None)

    # Relationship
    subscription: Subscription = Relationship(back_populates="payments")


class PaymentPublic(PaymentBase):
    """Public payment response."""

    id: uuid.UUID
    subscription_id: uuid.UUID
    provider: str
    provider_invoice_url: str | None
    period_start: datetime
    period_end: datetime
    created_at: datetime
    paid_at: datetime | None


class PaymentsPublic(SQLModel):
    """Paginated payments response."""

    data: list[PaymentPublic]
    count: int


# Subscription API Response Schemas
class SubscriptionCreateResponse(SQLModel):
    """Response when creating a subscription."""

    subscription_id: uuid.UUID
    payment_id: uuid.UUID
    payment_url: str | None
    amount: float
    message: str


class UserQuotaBase(SQLModel):
    sms_sent_this_month: int = Field(default=0)
    devices_registered: int = Field(default=0)
    last_reset_date: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserQuota(UserQuotaBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", unique=True, nullable=False, ondelete="CASCADE"
    )
    plan_id: uuid.UUID = Field(
        foreign_key="userplan.id", nullable=False, ondelete="RESTRICT"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    user: "User" = Relationship(back_populates="quota")
    plan: UserPlan = Relationship(back_populates="quotas")


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str | None = Field(default=None)  # Nullable for OAuth-only users
    email_verified_at: datetime | None = Field(default=None)
    sms_devices: list["SMSDevice"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    sms_messages: list["SMSMessage"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    webhook_configs: list["WebhookConfig"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    api_keys: list["ApiKey"] = Relationship(back_populates="user", cascade_delete=True)
    quota: UserQuota | None = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    oauth_accounts: list["OAuthAccount"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    subscription: Optional["Subscription"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UserPlanInfo(SQLModel):
    """Plan info included in user response."""

    plan_name: str
    max_sms_per_month: int
    max_devices: int
    sms_sent_this_month: int = 0
    devices_registered: int = 0
    subscription_status: str | None = None
    subscription_ends_at: datetime | None = None
    has_auto_renewal: bool = False


class UserPublicWithPlan(UserPublic):
    """User with plan information."""

    plan: UserPlanInfo | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# SMS Models
class SMSDeviceBase(SQLModel):
    name: str = Field(max_length=255)
    phone_number: str = Field(max_length=20)


class SMSDeviceCreate(SMSDeviceBase):
    pass


class SMSDeviceUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)


class SMSDevice(SMSDeviceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    api_key: str = Field(unique=True, index=True, max_length=255)
    fcm_token: str | None = Field(default=None, max_length=255)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    user: "User" = Relationship(back_populates="sms_devices")
    messages: list["SMSMessage"] = Relationship(
        back_populates="device", cascade_delete=True
    )


class SMSDevicePublic(SMSDeviceBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SMSDevicesPublic(SQLModel):
    data: list[SMSDevicePublic]
    count: int


class SMSMessageBase(SQLModel):
    to: str = Field(max_length=20)
    from_number: str | None = Field(default=None, max_length=20)
    body: str = Field(max_length=1600)
    status: str = Field(
        default="pending", max_length=50
    )  # pending, assigned, sending, sent, delivered, failed
    message_type: str = Field(default="outgoing", max_length=50)  # outgoing, incoming


class SMSMessageCreate(SQLModel):
    recipients: list[str] = Field(min_items=1, max_items=1000)
    body: str = Field(max_length=1600)
    device_id: uuid.UUID | None = None


class SMSReport(SQLModel):
    message_id: uuid.UUID
    status: str = Field(max_length=50)
    error_message: str | None = Field(default=None, max_length=500)


class SMSIncoming(SQLModel):
    from_number: str = Field(max_length=20)
    body: str = Field(max_length=1600)
    timestamp: str | None = Field(default=None)


class FCMTokenUpdate(SQLModel):
    fcm_token: str = Field(max_length=255)


class PlanUpgrade(SQLModel):
    plan_id: uuid.UUID


class SMSMessageUpdate(SQLModel):
    status: str | None = Field(default=None, max_length=50)
    from_number: str | None = Field(default=None, max_length=20)


class SMSMessage(SMSMessageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    batch_id: uuid.UUID | None = Field(default=None, index=True)  # Groups bulk messages
    device_id: uuid.UUID | None = Field(
        foreign_key="smsdevice.id", nullable=True, ondelete="SET NULL"
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    webhook_sent: bool = Field(default=False)
    error_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    sent_at: datetime | None = Field(default=None)
    delivered_at: datetime | None = Field(default=None)

    device: SMSDevice | None = Relationship(back_populates="messages")
    user: "User" = Relationship(back_populates="sms_messages")


class SMSMessagePublic(SMSMessageBase):
    id: uuid.UUID
    batch_id: uuid.UUID | None
    device_id: uuid.UUID | None
    user_id: uuid.UUID
    webhook_sent: bool
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None
    delivered_at: datetime | None


class SMSMessagesPublic(SQLModel):
    data: list[SMSMessagePublic]
    count: int


class SMSMessageSendPublic(SQLModel):
    batch_id: uuid.UUID | None  # None if single recipient
    message_ids: list[uuid.UUID]
    recipients_count: int
    status: str


class SMSDeviceCreatePublic(SQLModel):
    device_id: uuid.UUID
    api_key: str


class WebhookConfigBase(SQLModel):
    url: str = Field(max_length=500)
    secret_key: str | None = Field(default=None, max_length=255)
    events: str = Field(default='["sms_received"]', max_length=500)  # JSON string
    active: bool = Field(default=True)


class WebhookConfigCreate(WebhookConfigBase):
    pass


class WebhookConfigUpdate(SQLModel):
    url: str | None = Field(default=None, max_length=500)
    secret_key: str | None = Field(default=None, max_length=255)
    events: str | None = Field(default=None, max_length=500)  # JSON string
    active: bool | None = None


class WebhookConfig(WebhookConfigBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    user: "User" = Relationship(back_populates="webhook_configs")


class WebhookConfigPublic(WebhookConfigBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class WebhookConfigsPublic(SQLModel):
    data: list[WebhookConfigPublic]
    count: int


class UserPlanCreate(UserPlanBase):
    pass


class UserPlanPublic(UserPlanBase):
    id: uuid.UUID
    price_yearly: float
    is_public: bool
    created_at: datetime
    updated_at: datetime


class UserPlansPublic(SQLModel):
    data: list[UserPlanPublic]
    count: int


class UserQuotaPublic(SQLModel):
    plan: str
    sms_sent_this_month: int
    max_sms_per_month: int
    devices_registered: int
    max_devices: int
    reset_date: str | None


class PlanUpgradeRequest(SQLModel):
    """Request body for plan upgrade."""

    plan_id: uuid.UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_method: PaymentMethod | None = None  # None = use system default


class PlanUpgradePublic(SQLModel):
    message: str
    data: dict[str, str]


# API Key Models (for integrations like n8n, Zapier, etc.)
class ApiKeyBase(SQLModel):
    name: str = Field(max_length=255)
    is_active: bool = Field(default=True)


class ApiKeyCreate(SQLModel):
    name: str = Field(max_length=255)


class ApiKey(ApiKeyBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=255)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    user: "User" = Relationship(back_populates="api_keys")


class ApiKeyPublic(ApiKeyBase):
    id: uuid.UUID
    key_prefix: str  # Only show first 8 chars for security
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreatePublic(SQLModel):
    id: uuid.UUID
    name: str
    key: str  # Full key shown only on creation
    created_at: datetime


class ApiKeysPublic(SQLModel):
    data: list[ApiKeyPublic]
    count: int


# OAuth Account Models
class OAuthAccountBase(SQLModel):
    provider: str = Field(max_length=50, index=True)  # "google" | "github"
    provider_user_id: str = Field(max_length=255)
    provider_email: str = Field(max_length=255)


class OAuthAccount(OAuthAccountBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    access_token: str | None = Field(default=None, max_length=2000)
    refresh_token: str | None = Field(default=None, max_length=2000)
    token_expires_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    user: "User" = Relationship(back_populates="oauth_accounts")


class OAuthAccountPublic(OAuthAccountBase):
    id: uuid.UUID
    created_at: datetime


class OAuthAccountsPublic(SQLModel):
    data: list[OAuthAccountPublic]
    count: int


# OAuth API Schemas
class OAuthProviderInfo(SQLModel):
    name: str
    enabled: bool


class OAuthProvidersResponse(SQLModel):
    providers: list[OAuthProviderInfo]


class OAuthAuthorizeResponse(SQLModel):
    authorization_url: str


class OAuthCallbackResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool = False
    requires_linking: bool = False
    existing_email: str | None = None


class OAuthLinkRequest(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)


class SetPasswordRequest(SQLModel):
    new_password: str = Field(min_length=8, max_length=128)


# System Configuration Models
class SystemConfig(SQLModel, table=True):
    """
    System-wide configuration stored in database.

    Allows runtime configuration changes without redeployment.
    Environment variables serve as defaults, DB values override them.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=100)
    value: str = Field(max_length=1000)
    description: str | None = Field(default=None, max_length=500)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )


class SystemConfigPublic(SQLModel):
    """Public system config response."""

    key: str
    value: str
    description: str | None
    category: str | None = None
    updated_at: datetime


class SystemConfigUpdate(SQLModel):
    """Update a system config value."""

    value: str = Field(max_length=1000)


class SystemConfigsPublic(SQLModel):
    """List of system configs."""

    data: list[SystemConfigPublic]
    count: int
