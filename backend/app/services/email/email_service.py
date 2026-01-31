"""
Email service with provider abstraction.

This module provides a unified interface for sending emails, regardless of the
underlying provider (Maileroo, SMTP, SendGrid, etc.).

To switch providers, simply change the EMAIL_PROVIDER environment variable.
"""

import logging
from enum import Enum
from functools import lru_cache

from app.core.config import settings

from .base import EmailMessage, EmailProvider, EmailResult, EmailStatus
from .maileroo_provider import MailerooProvider
from .smtp_provider import SMTPProvider

logger = logging.getLogger(__name__)


class EmailProviderType(str, Enum):
    """Supported email provider types."""

    SMTP = "smtp"
    MAILEROO = "maileroo"
    # Future providers can be added here:
    # SENDGRID = "sendgrid"
    # MAILGUN = "mailgun"
    # AWS_SES = "aws_ses"
    # POSTMARK = "postmark"


class EmailService:
    """
    Main email service that abstracts provider selection.

    This service:
    - Automatically selects the configured provider
    - Provides a unified API for sending emails
    - Handles provider initialization and configuration

    Usage:
        service = EmailService()
        result = await service.send_email(
            to="user@example.com",
            subject="Welcome!",
            html_content="<h1>Hello!</h1>",
        )

    Configuration (via environment variables):
        EMAIL_PROVIDER: Provider to use (smtp, maileroo, etc.)

        For SMTP:
            SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
            SMTP_TLS, SMTP_SSL
            EMAILS_FROM_EMAIL, EMAILS_FROM_NAME

        For Maileroo:
            MAILEROO_API_KEY
            EMAILS_FROM_EMAIL, EMAILS_FROM_NAME
    """

    def __init__(self, provider: EmailProvider | None = None):
        """
        Initialize the email service.

        Args:
            provider: Optional provider instance. If not provided,
                     will be auto-detected from configuration.
        """
        self._provider = provider

    @property
    def provider(self) -> EmailProvider:
        """Get the email provider, initializing if needed."""
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> EmailProvider:
        """Create the appropriate provider based on configuration."""
        provider_type = getattr(settings, "EMAIL_PROVIDER", "smtp").lower()

        if provider_type == EmailProviderType.MAILEROO:
            return MailerooProvider(
                api_key=getattr(settings, "MAILEROO_API_KEY", None),
                from_email=settings.EMAILS_FROM_EMAIL,
                from_name=settings.EMAILS_FROM_NAME,
            )
        else:
            # Default to SMTP
            return SMTPProvider(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                from_email=settings.EMAILS_FROM_EMAIL,
                from_name=settings.EMAILS_FROM_NAME,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
                use_ssl=settings.SMTP_SSL,
            )

    def is_configured(self) -> bool:
        """Check if email sending is properly configured."""
        return self.provider.is_configured()

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        reply_to: str | None = None,
        tags: list[str] | None = None,
    ) -> EmailResult:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body (optional)
            from_email: Sender email (optional, uses default)
            from_name: Sender name (optional, uses default)
            reply_to: Reply-to address (optional)
            tags: Tags for tracking (optional)

        Returns:
            EmailResult with send status
        """
        if not self.is_configured():
            logger.warning("Email service is not configured, skipping send")
            return EmailResult(
                status=EmailStatus.FAILED,
                error="Email service is not configured",
            )

        message = EmailMessage(
            to=to,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=from_email,
            from_name=from_name,
            reply_to=reply_to,
            tags=tags,
        )

        return await self.provider.send(message)

    async def send_batch(
        self,
        messages: list[EmailMessage],
    ) -> list[EmailResult]:
        """
        Send multiple emails.

        Args:
            messages: List of email messages

        Returns:
            List of EmailResult for each message
        """
        if not self.is_configured():
            logger.warning("Email service is not configured, skipping batch send")
            return [
                EmailResult(
                    status=EmailStatus.FAILED,
                    error="Email service is not configured",
                )
                for _ in messages
            ]

        return await self.provider.send_batch(messages)


# Singleton instance
_email_service: EmailService | None = None


@lru_cache
def get_email_service() -> EmailService:
    """
    Get the email service singleton.

    Returns:
        EmailService instance
    """
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
