import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import EmailStr
from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


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


class UserPlan(UserPlanBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    quotas: list["UserQuota"] = Relationship(back_populates="plan")


class UserQuotaBase(SQLModel):
    sms_sent_this_month: int = Field(default=0)
    devices_registered: int = Field(default=0)
    last_reset_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UserQuota(UserQuotaBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", unique=True, nullable=False, ondelete="CASCADE"
    )
    plan_id: uuid.UUID = Field(
        foreign_key="userplan.id", nullable=False, ondelete="RESTRICT"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    user: "User" = Relationship(back_populates="quota")
    plan: UserPlan = Relationship(back_populates="quotas")


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    sms_devices: list["SMSDevice"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    sms_messages: list["SMSMessage"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    webhook_configs: list["WebhookConfig"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    quota: UserQuota | None = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


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
    status: str = Field(default="offline", max_length=50)  # offline, online, idle, busy


class SMSDeviceCreate(SMSDeviceBase):
    pass


class SMSDeviceUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=50)


class SMSDevice(SMSDeviceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    api_key: str = Field(unique=True, index=True, max_length=255)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    last_heartbeat: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    user: "User" = Relationship(back_populates="sms_devices")
    messages: list["SMSMessage"] = Relationship(
        back_populates="device", cascade_delete=True
    )


class SMSDevicePublic(SMSDeviceBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str = Field(default="offline", max_length=50)  # offline, online, idle, busy
    last_heartbeat: datetime | None
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


class SMSMessageCreate(SMSMessageBase):
    device_id: uuid.UUID | None = None


class SMSBulkCreate(SQLModel):
    recipients: list[str] = Field(min_items=1, max_items=1000)
    body: str = Field(max_length=1600)
    device_id: uuid.UUID | None = None


class PlanUpgrade(SQLModel):
    plan_id: uuid.UUID


class SMSMessageUpdate(SQLModel):
    status: str | None = Field(default=None, max_length=50)
    from_number: str | None = Field(default=None, max_length=20)


class SMSMessage(SMSMessageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    device_id: uuid.UUID | None = Field(
        foreign_key="smsdevice.id", nullable=True, ondelete="SET NULL"
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    webhook_sent: bool = Field(default=False)
    error_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
    sent_at: datetime | None = Field(default=None)
    delivered_at: datetime | None = Field(default=None)

    device: SMSDevice | None = Relationship(back_populates="messages")
    user: "User" = Relationship(back_populates="sms_messages")


class SMSMessagePublic(SMSMessageBase):
    id: uuid.UUID
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
    message_id: uuid.UUID
    status: str


class SMSBulkSendPublic(SQLModel):
    total_recipients: int
    status: str
    message_ids: list[uuid.UUID]


class SMSDeviceCreatePublic(SQLModel):
    device_id: uuid.UUID
    api_key: str
    status: str


class SMSOutbox(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sms_message_id: uuid.UUID = Field(foreign_key="smsmessage.id", index=True)
    device_id: uuid.UUID | None = Field(foreign_key="smsdevice.id", nullable=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSON))
    status: str = Field(
        default="pending", max_length=50, index=True
    )  # pending, sending, sent, failed, retry
    attempts: int = Field(default=0)
    next_attempt_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
    sending_at: datetime | None = Field(default=None)

    sms_message: SMSMessage = Relationship()
    device: SMSDevice | None = Relationship()


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
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


class PlanUpgradePublic(SQLModel):
    message: str
    data: dict[str, str]
