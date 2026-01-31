"""
SMTP email provider implementation.

This provider uses standard SMTP protocol to send emails.
Useful for development (with Mailcatcher) or self-hosted SMTP servers.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .base import EmailMessage, EmailProvider, EmailResult, EmailStatus

logger = logging.getLogger(__name__)


class SMTPProvider(EmailProvider):
    """
    Email provider implementation using SMTP.

    This is useful for:
    - Local development with Mailcatcher
    - Self-hosted SMTP servers
    - Traditional email services that provide SMTP access

    Required configuration:
        - host: SMTP server hostname
        - port: SMTP server port
        - from_email: Default sender email
        - from_name: Default sender name (optional)
        - username: SMTP auth username (optional)
        - password: SMTP auth password (optional)
        - use_tls: Use STARTTLS (default: True)
        - use_ssl: Use SSL/TLS (default: False)

    Usage:
        provider = SMTPProvider(
            host="localhost",
            port=1025,
            from_email="noreply@example.com",
            use_tls=False,
        )
        result = await provider.send(message)
    """

    def __init__(
        self,
        host: str | None = None,
        port: int = 587,
        from_email: str | None = None,
        from_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        use_ssl: bool = False,
    ):
        self.host = host
        self.port = port
        self.from_email = from_email
        self.from_name = from_name
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(self.host and self.from_email)

    def _build_message(self, message: EmailMessage) -> MIMEMultipart:
        """Build a MIME message from EmailMessage."""
        msg = MIMEMultipart("alternative")

        # Set headers
        from_email = message.from_email or self.from_email
        from_name = message.from_name or self.from_name

        if from_name:
            msg["From"] = f"{from_name} <{from_email}>"
        else:
            msg["From"] = from_email

        msg["To"] = message.to
        msg["Subject"] = message.subject

        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        # Add content parts
        if message.text_content:
            text_part = MIMEText(message.text_content, "plain", "utf-8")
            msg.attach(text_part)

        if message.html_content:
            html_part = MIMEText(message.html_content, "html", "utf-8")
            msg.attach(html_part)

        return msg

    def _send_sync(self, message: EmailMessage) -> EmailResult:
        """Synchronous send implementation."""
        if not self.is_configured():
            return EmailResult(
                status=EmailStatus.FAILED,
                error="SMTP is not configured. Missing host or from_email.",
            )

        try:
            mime_message = self._build_message(message)
            from_email = message.from_email or self.from_email

            # Create SMTP connection
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=30)

            try:
                if self.use_tls and not self.use_ssl:
                    server.starttls()

                if self.username and self.password:
                    server.login(self.username, self.password)

                server.sendmail(from_email, message.to, mime_message.as_string())

                logger.info(f"Email sent successfully via SMTP to {message.to}")
                return EmailResult(
                    status=EmailStatus.SENT,
                    message_id=mime_message["Message-ID"],
                )
            finally:
                server.quit()

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return EmailResult(
                status=EmailStatus.FAILED,
                error=f"Authentication failed: {e}",
            )
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return EmailResult(
                status=EmailStatus.FAILED,
                error=f"Recipient refused: {e}",
            )
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return EmailResult(
                status=EmailStatus.FAILED,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email via SMTP: {e}")
            return EmailResult(
                status=EmailStatus.FAILED,
                error=str(e),
            )

    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Send an email via SMTP.

        Runs the synchronous SMTP operations in a thread pool.

        Args:
            message: The email message to send

        Returns:
            EmailResult with status
        """
        # Run synchronous SMTP in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_sync, message)
