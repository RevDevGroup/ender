"""
System configuration API routes.

Allows admins to manage runtime system settings.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, get_current_active_superuser
from app.core.config import settings
from app.models import (
    PaymentMethod,
    SystemConfig,
    SystemConfigPublic,
    SystemConfigsPublic,
    SystemConfigUpdate,
)

router = APIRouter(
    prefix="/system-config",
    tags=["system-config"],
    dependencies=[Depends(get_current_active_superuser)],
)

# Known configuration keys with their defaults, descriptions, and categories
CONFIG_DEFINITIONS: dict[str, dict[str, Any]] = {
    # General settings
    "app_name": {
        "default": lambda: settings.PROJECT_NAME,
        "description": "Application display name",
        "category": "general",
    },
    "support_email": {
        "default": lambda: settings.EMAILS_FROM_EMAIL or "support@example.com",
        "description": "Support contact email address",
        "category": "general",
    },
    "maintenance_mode": {
        "default": lambda: "false",
        "description": "Enable maintenance mode (true/false)",
        "category": "general",
        "allowed_values": ["true", "false"],
    },
    # Payment settings
    "default_payment_method": {
        "default": lambda: getattr(settings, "DEFAULT_PAYMENT_METHOD", "invoice"),
        "description": "Default payment method for subscriptions (invoice or authorized)",
        "category": "payments",
        "allowed_values": ["invoice", "authorized"],
    },
    # SMS settings
    "sms_retry_attempts": {
        "default": lambda: "3",
        "description": "Number of retry attempts for failed SMS",
        "category": "sms",
    },
    # Notifications settings
    "email_notifications_enabled": {
        "default": lambda: "true",
        "description": "Enable email notifications (true/false)",
        "category": "notifications",
        "allowed_values": ["true", "false"],
    },
    "webhook_timeout_seconds": {
        "default": lambda: "30",
        "description": "Timeout for webhook delivery in seconds",
        "category": "notifications",
    },
}


def get_config_value(session: Any, key: str) -> str:
    """Get config value from DB, falling back to env/default."""
    config = session.exec(select(SystemConfig).where(SystemConfig.key == key)).first()
    if config:
        return str(config.value)

    # Fall back to definition default
    if key in CONFIG_DEFINITIONS:
        return str(CONFIG_DEFINITIONS[key]["default"]())

    raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")


@router.get("/", response_model=SystemConfigsPublic)
def list_configs(session: SessionDep) -> SystemConfigsPublic:
    """List all system configuration settings."""
    # Get all configs from DB
    db_configs = session.exec(select(SystemConfig)).all()
    db_config_map = {c.key: c for c in db_configs}

    # Build response with all known configs
    configs: list[SystemConfigPublic] = []
    for key, definition in CONFIG_DEFINITIONS.items():
        if key in db_config_map:
            config = db_config_map[key]
            configs.append(
                SystemConfigPublic(
                    key=config.key,
                    value=config.value,
                    description=config.description or definition["description"],
                    category=definition.get("category"),
                    updated_at=config.updated_at,
                )
            )
        else:
            # Return default value
            from datetime import UTC, datetime

            configs.append(
                SystemConfigPublic(
                    key=key,
                    value=definition["default"](),
                    description=definition["description"],
                    category=definition.get("category"),
                    updated_at=datetime.now(UTC),
                )
            )

    return SystemConfigsPublic(data=configs, count=len(configs))


@router.get("/{key}", response_model=SystemConfigPublic)
def get_config(key: str, session: SessionDep) -> SystemConfigPublic:
    """Get a specific configuration value."""
    if key not in CONFIG_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

    config = session.exec(select(SystemConfig).where(SystemConfig.key == key)).first()
    definition = CONFIG_DEFINITIONS[key]

    if config:
        return SystemConfigPublic(
            key=config.key,
            value=config.value,
            description=config.description or definition["description"],
            category=definition.get("category"),
            updated_at=config.updated_at,
        )

    # Return default
    from datetime import UTC, datetime

    return SystemConfigPublic(
        key=key,
        value=definition["default"](),
        description=definition["description"],
        category=definition.get("category"),
        updated_at=datetime.now(UTC),
    )


@router.put("/{key}", response_model=SystemConfigPublic)
def update_config(
    key: str, body: SystemConfigUpdate, session: SessionDep
) -> SystemConfigPublic:
    """Update a configuration value."""
    if key not in CONFIG_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

    definition = CONFIG_DEFINITIONS[key]

    # Validate value if allowed_values is defined
    if "allowed_values" in definition:
        if body.value not in definition["allowed_values"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value. Allowed: {definition['allowed_values']}",
            )

    config = session.exec(select(SystemConfig).where(SystemConfig.key == key)).first()

    if config:
        config.value = body.value
    else:
        config = SystemConfig(
            key=key,
            value=body.value,
            description=definition["description"],
        )
        session.add(config)

    session.commit()
    session.refresh(config)

    return SystemConfigPublic(
        key=config.key,
        value=config.value,
        description=config.description or definition["description"],
        category=definition.get("category"),
        updated_at=config.updated_at,
    )


# Helper function for other services to get config values
def get_default_payment_method(session: Any) -> PaymentMethod:
    """Get the default payment method from system config."""
    value = get_config_value(session, "default_payment_method")
    return PaymentMethod(value)
