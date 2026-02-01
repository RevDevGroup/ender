import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
from jinja2 import Template
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.services.email import get_email_service
from app.services.email.base import EmailStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


class EmailNotConfiguredError(Exception):
    """Raised when email sending is attempted but not configured."""

    pass


class EmailSendError(Exception):
    """Raised when email sending fails."""

    pass


def get_support_email_from_config() -> str | None:
    """Get support email from system config for use as reply-to."""
    try:
        from app.core.db import engine
        from app.services.config_service import ConfigService

        with Session(engine) as session:
            return ConfigService.get_support_email(session)
    except Exception:
        return None


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
    reply_to: str | None = None,
) -> None:
    """
    Send an email using the configured email provider.

    Uses the EmailService which supports multiple providers (SMTP, Maileroo, etc.)
    based on the EMAIL_PROVIDER environment variable.

    If reply_to is not provided, uses the support_email from system config.
    """
    email_service = get_email_service()

    if not email_service.is_configured():
        raise EmailNotConfiguredError("Email service is not configured")

    # Use support_email as reply-to if not explicitly provided
    if reply_to is None:
        reply_to = get_support_email_from_config()

    # Run the async send_email in a sync context
    result = asyncio.run(
        email_service.send_email(
            to=email_to,
            subject=subject,
            html_content=html_content,
            reply_to=reply_to,
        )
    )

    if result.status == EmailStatus.FAILED:
        logger.error(f"Failed to send email to {email_to}: {result.error}")
        raise EmailSendError(result.error or "Failed to send email")

    logger.info(f"Email sent to {email_to}, message_id: {result.message_id}")


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    support_email = get_support_email_from_config() or settings.EMAILS_FROM_EMAIL
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
            "support_email": support_email,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    support_email = get_support_email_from_config() or settings.EMAILS_FROM_EMAIL
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
            "support_email": support_email,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_email_verification_email(email_to: str, token: str) -> EmailData:
    """Generate email verification email content."""
    project_name = settings.PROJECT_NAME
    support_email = get_support_email_from_config() or settings.EMAILS_FROM_EMAIL
    subject = f"{project_name} - Verify your email address"
    link = f"{settings.FRONTEND_HOST}/verify-email?token={token}"
    html_content = render_email_template(
        template_name="verify_email.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email_to,
            "valid_hours": settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
            "link": link,
            "support_email": support_email,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_email_verification_token(email: str) -> str:
    """Generate a JWT token for email verification."""
    delta = timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    now = datetime.now(UTC)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "email_verification"},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_email_verification_token(token: str) -> str | None:
    """
    Verify an email verification token.

    Returns the email if valid, None otherwise.
    """
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        # Check that it's an email verification token
        if decoded_token.get("type") != "email_verification":
            return None
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(UTC)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


def validate_sms_device(
    *, session: Session, device_id: uuid.UUID | None, user_id: uuid.UUID
) -> None:
    """
    Valida que un dispositivo SMS existe y pertenece al usuario.

    Args:
        session: Sesión de base de datos
        device_id: ID del dispositivo a validar (opcional)
        user_id: ID del usuario que debe ser dueño del dispositivo

    Raises:
        ValueError: Si el dispositivo no existe o no pertenece al usuario
    """
    if device_id is None:
        return

    # Importar aquí para evitar circular imports
    from app.crud import get_sms_device

    device = get_sms_device(session=session, device_id=device_id)
    if device is None:
        raise ValueError(f"Device with id {device_id} not found")
    if device.user_id != user_id:
        raise ValueError(f"Device {device_id} does not belong to user")
