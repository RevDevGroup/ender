"""
Base email provider interface.

This module defines the abstract base class that all email providers must implement.
To add a new provider, create a new class that inherits from EmailProvider and
implements all abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class EmailStatus(Enum):
    """Status of an email send operation."""

    SENT = "sent"
    QUEUED = "queued"
    FAILED = "failed"


@dataclass
class EmailMessage:
    """
    Represents an email message to be sent.

    Attributes:
        to: Recipient email address
        subject: Email subject line
        html_content: HTML body of the email
        text_content: Plain text body (optional, for fallback)
        from_email: Sender email (optional, uses default if not provided)
        from_name: Sender name (optional, uses default if not provided)
        reply_to: Reply-to address (optional)
        tags: List of tags for tracking (optional, provider-dependent)
    """

    to: str
    subject: str
    html_content: str
    text_content: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    tags: list[str] | None = None


@dataclass
class EmailResult:
    """
    Result of an email send operation.

    Attributes:
        status: Status of the send operation
        message_id: Provider-specific message ID (if available)
        error: Error message if status is FAILED
        raw_response: Raw response from provider (for debugging)
    """

    status: EmailStatus
    message_id: str | None = None
    error: str | None = None
    raw_response: dict | None = None


class EmailProvider(ABC):
    """
    Abstract base class for email providers.

    To implement a new provider:
    1. Create a new class that inherits from EmailProvider
    2. Implement the `send` method
    3. Implement the `send_batch` method (optional, default uses sequential sends)
    4. Register the provider in EmailService

    Example:
        class MyProvider(EmailProvider):
            def __init__(self, api_key: str):
                self.api_key = api_key

            async def send(self, message: EmailMessage) -> EmailResult:
                # Implementation here
                pass
    """

    @abstractmethod
    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Send a single email message.

        Args:
            message: The email message to send

        Returns:
            EmailResult with the status of the operation
        """
        pass

    async def send_batch(self, messages: list[EmailMessage]) -> list[EmailResult]:
        """
        Send multiple email messages.

        Default implementation sends sequentially. Override for batch API support.

        Args:
            messages: List of email messages to send

        Returns:
            List of EmailResult for each message
        """
        results = []
        for message in messages:
            result = await self.send(message)
            results.append(result)
        return results

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.

        Returns:
            True if the provider has all required configuration
        """
        pass
