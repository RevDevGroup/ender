"""
Base OAuth provider interface.

This module defines the abstract base class that all OAuth providers must implement.
To add a new provider, create a new class that inherits from OAuthProvider and
implements all abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OAuthTokens:
    """
    OAuth tokens received from the provider.

    Attributes:
        access_token: Token for accessing provider APIs
        refresh_token: Token for refreshing access (optional)
        expires_at: When the access token expires (optional)
        token_type: Type of token (usually "Bearer")
    """

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    token_type: str = "Bearer"


@dataclass
class OAuthUserInfo:
    """
    User information from OAuth provider.

    Attributes:
        provider: Name of the OAuth provider (e.g., "google", "github")
        provider_user_id: Unique user ID from the provider
        email: User's email address
        name: User's full name (optional)
        picture: URL to user's profile picture (optional)
        email_verified: Whether the email is verified by the provider
    """

    provider: str
    provider_user_id: str
    email: str
    name: str | None = None
    picture: str | None = None
    email_verified: bool = False


class OAuthProvider(ABC):
    """
    Abstract base class for OAuth providers.

    To implement a new provider:
    1. Create a new class that inherits from OAuthProvider
    2. Implement all abstract methods
    3. Register the provider in OAuthService

    Example:
        class MyProvider(OAuthProvider):
            def __init__(self, client_id: str, client_secret: str):
                self.client_id = client_id
                self.client_secret = client_secret

            def get_authorization_url(self, state: str, redirect_uri: str) -> str:
                # Implementation here
                pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'google', 'github')."""
        pass

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Generate the OAuth authorization URL.

        Args:
            state: Random state parameter for CSRF protection
            redirect_uri: URL to redirect to after authorization

        Returns:
            The full authorization URL to redirect the user to
        """
        pass

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        """
        Exchange authorization code for access tokens.

        Args:
            code: The authorization code from the callback
            redirect_uri: The same redirect URI used in authorization

        Returns:
            OAuthTokens containing access and refresh tokens
        """
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Fetch user information using the access token.

        Args:
            access_token: Valid access token from exchange_code

        Returns:
            OAuthUserInfo with user details from the provider
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.

        Returns:
            True if the provider has all required configuration
        """
        pass
