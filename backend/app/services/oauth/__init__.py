"""
OAuth service layer.

This module provides OAuth authentication support for multiple providers.
"""

from app.services.oauth.base import OAuthProvider, OAuthTokens, OAuthUserInfo
from app.services.oauth.oauth_service import OAuthService, get_oauth_service

__all__ = [
    "OAuthProvider",
    "OAuthTokens",
    "OAuthUserInfo",
    "OAuthService",
    "get_oauth_service",
]
