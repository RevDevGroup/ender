"""
Maileroo email provider implementation using the official SDK.

Documentation: https://maileroo.com/docs/email-api/libraries-and-sdks/
PyPI: https://pypi.org/project/maileroo/
"""

import logging

from maileroo import MailerooClient

from .base import EmailMessage, EmailProvider, EmailResult, EmailStatus

logger = logging.getLogger(__name__)


class MailerooProvider(EmailProvider):
    """
    Email provider implementation for Maileroo using the official Python SDK.

    Required configuration:
        - api_key: Your Maileroo sending key (from domain settings)
        - from_email: Default sender email (must be from verified domain)
        - from_name: Default sender name (optional)

    Usage:
        provider = MailerooProvider(
            api_key="your-api-key",
            from_email="noreply@yourdomain.com",
            from_name="Your App"
        )
        result = await provider.send(message)
    """

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self._client = None

    def _get_client(self):
        """Lazy initialization of the Maileroo client."""
        if self._client is None:
            self._client = MailerooClient(self.api_key)
        return self._client

    def is_configured(self) -> bool:
        """Check if Maileroo is properly configured."""
        return bool(self.api_key and self.from_email)

    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Send an email via Maileroo SDK.

        Args:
            message: The email message to send

        Returns:
            EmailResult with status and message_id (reference_id from Maileroo)
        """
        if not self.is_configured():
            return EmailResult(
                status=EmailStatus.FAILED,
                error="Maileroo is not configured. Missing API key or from_email.",
            )

        try:
            from maileroo import EmailAddress

            client = self._get_client()

            # Build from address
            from_email = message.from_email or self.from_email
            from_name = message.from_name or self.from_name
            from_addr = (
                EmailAddress(from_email, from_name)
                if from_name
                else EmailAddress(from_email)
            )

            # Build to address
            to_addr = [EmailAddress(message.to)]

            # Build email payload
            email_data: dict = {
                "from": from_addr,
                "to": to_addr,
                "subject": message.subject,
            }

            if message.html_content:
                email_data["html"] = message.html_content
            if message.text_content:
                email_data["plain"] = message.text_content
            if message.reply_to:
                email_data["reply_to"] = [EmailAddress(message.reply_to)]

            # Send the email
            reference_id = client.send_basic_email(email_data)

            logger.info(
                f"Email sent successfully via Maileroo to {message.to}, "
                f"reference_id: {reference_id}"
            )
            return EmailResult(
                status=EmailStatus.SENT,
                message_id=reference_id,
            )

        except ImportError:
            logger.error("Maileroo SDK not installed. Run: pip install maileroo")
            return EmailResult(
                status=EmailStatus.FAILED,
                error="Maileroo SDK not installed",
            )
        except Exception as e:
            logger.error(f"Failed to send email via Maileroo to {message.to}: {e}")
            return EmailResult(
                status=EmailStatus.FAILED,
                error=str(e),
            )
