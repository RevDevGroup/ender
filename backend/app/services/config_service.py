"""
System configuration service.

Provides runtime configuration values from database with env fallbacks.
"""

from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.models import PaymentMethod, SystemConfig

# Configuration definitions with defaults
CONFIG_DEFAULTS: dict[str, Any] = {
    "app_name": lambda: settings.PROJECT_NAME,
    "support_email": lambda: settings.EMAILS_FROM_EMAIL or "support@example.com",
    "maintenance_mode": lambda: "false",
    "default_payment_method": lambda: getattr(
        settings, "DEFAULT_PAYMENT_METHOD", "invoice"
    ),
    "payment_provider": lambda: settings.PAYMENT_PROVIDER,
    "sms_rate_limit_per_minute": lambda: "60",
    "sms_retry_attempts": lambda: "3",
    "email_notifications_enabled": lambda: "true",
    "webhook_timeout_seconds": lambda: "30",
}


class ConfigService:
    """Service for reading system configuration."""

    @staticmethod
    def get_value(session: Session, key: str) -> str:
        """Get config value from DB, falling back to default."""
        config = session.exec(
            select(SystemConfig).where(SystemConfig.key == key)
        ).first()
        if config:
            return str(config.value)

        if key in CONFIG_DEFAULTS:
            return str(CONFIG_DEFAULTS[key]())

        raise ValueError(f"Unknown config key: {key}")

    @staticmethod
    def get_bool(session: Session, key: str) -> bool:
        """Get config value as boolean."""
        return ConfigService.get_value(session, key).lower() == "true"

    @staticmethod
    def get_int(session: Session, key: str) -> int:
        """Get config value as integer."""
        return int(ConfigService.get_value(session, key))

    # Typed helper methods for specific configs
    @staticmethod
    def get_app_name(session: Session) -> str:
        """Get application display name."""
        return ConfigService.get_value(session, "app_name")

    @staticmethod
    def get_support_email(session: Session) -> str:
        """Get support email address."""
        return ConfigService.get_value(session, "support_email")

    @staticmethod
    def is_maintenance_mode(session: Session) -> bool:
        """Check if maintenance mode is enabled."""
        return ConfigService.get_bool(session, "maintenance_mode")

    @staticmethod
    def get_default_payment_method(session: Session) -> PaymentMethod:
        """Get default payment method for subscriptions."""
        value = ConfigService.get_value(session, "default_payment_method")
        return PaymentMethod(value)

    @staticmethod
    def get_payment_provider(session: Session) -> str:
        """Get active payment provider name."""
        return ConfigService.get_value(session, "payment_provider")

    @staticmethod
    def get_sms_rate_limit(session: Session) -> int:
        """Get SMS rate limit per minute."""
        return ConfigService.get_int(session, "sms_rate_limit_per_minute")

    @staticmethod
    def get_sms_retry_attempts(session: Session) -> int:
        """Get number of SMS retry attempts."""
        return ConfigService.get_int(session, "sms_retry_attempts")

    @staticmethod
    def is_email_notifications_enabled(session: Session) -> bool:
        """Check if email notifications are enabled."""
        return ConfigService.get_bool(session, "email_notifications_enabled")

    @staticmethod
    def get_webhook_timeout(session: Session) -> int:
        """Get webhook timeout in seconds."""
        return ConfigService.get_int(session, "webhook_timeout_seconds")
