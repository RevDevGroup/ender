"""
OAuth service orchestration.

This module provides the main OAuth service that coordinates between
different providers and handles user authentication/creation.
"""

from app.core.config import settings
from app.services.oauth.base import OAuthProvider
from app.services.oauth.github_provider import GitHubOAuthProvider
from app.services.oauth.google_provider import GoogleOAuthProvider


class OAuthService:
    """
    Main OAuth service that manages providers and authentication flow.

    Usage:
        service = OAuthService()
        providers = service.get_available_providers()
        provider = service.get_provider("google")
        url = provider.get_authorization_url(state, redirect_uri)
    """

    def __init__(self) -> None:
        self._providers: dict[str, OAuthProvider] = {
            "google": GoogleOAuthProvider(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            ),
            "github": GitHubOAuthProvider(
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
            ),
        }

    def get_provider(self, provider_name: str) -> OAuthProvider | None:
        """
        Get an OAuth provider by name.

        Args:
            provider_name: Name of the provider (e.g., "google", "github")

        Returns:
            The provider instance if found and configured, None otherwise
        """
        provider = self._providers.get(provider_name.lower())
        if provider and provider.is_configured():
            return provider
        return None

    def get_available_providers(self) -> list[dict[str, str | bool]]:
        """
        Get list of all providers with their configuration status.

        Returns:
            List of dicts with provider name and enabled status
        """
        return [
            {"name": name, "enabled": provider.is_configured()}
            for name, provider in self._providers.items()
        ]

    def get_enabled_providers(self) -> list[str]:
        """
        Get list of enabled provider names.

        Returns:
            List of provider names that are properly configured
        """
        return [
            name
            for name, provider in self._providers.items()
            if provider.is_configured()
        ]

    def is_provider_enabled(self, provider_name: str) -> bool:
        """
        Check if a specific provider is enabled.

        Args:
            provider_name: Name of the provider

        Returns:
            True if the provider exists and is configured
        """
        provider = self._providers.get(provider_name.lower())
        return provider is not None and provider.is_configured()


# Singleton instance
_oauth_service: OAuthService | None = None


def get_oauth_service() -> OAuthService:
    """Get or create the OAuth service singleton."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service
