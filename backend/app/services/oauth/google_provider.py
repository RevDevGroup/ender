"""
Google OAuth provider implementation.
"""

from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx

from app.services.oauth.base import OAuthProvider, OAuthTokens, OAuthUserInfo


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider."""

    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self, client_id: str | None, client_secret: str | None):
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    def name(self) -> str:
        return "google"

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Always show consent screen to get refresh token
        }
        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            response.raise_for_status()
            data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.now(UTC).replace(microsecond=0) + __import__(
                "datetime"
            ).timedelta(seconds=data["expires_in"])

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer"),
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

        return OAuthUserInfo(
            provider=self.name,
            provider_user_id=data["id"],
            email=data["email"],
            name=data.get("name"),
            picture=data.get("picture"),
            email_verified=data.get("verified_email", False),
        )
