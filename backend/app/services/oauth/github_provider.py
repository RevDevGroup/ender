"""
GitHub OAuth provider implementation.
"""

from urllib.parse import urlencode

import httpx

from app.services.oauth.base import OAuthProvider, OAuthTokens, OAuthUserInfo


class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth 2.0 provider."""

    AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USERINFO_URL = "https://api.github.com/user"
    EMAILS_URL = "https://api.github.com/user/emails"

    def __init__(self, client_id: str | None, client_secret: str | None):
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    def name(self) -> str:
        return "github"

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
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
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            raise ValueError(
                f"GitHub OAuth error: {data.get('error_description', data['error'])}"
            )

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=None,  # GitHub tokens don't expire by default
            token_type=data.get("token_type", "Bearer"),
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            # Get user profile
            response = await client.get(
                self.USERINFO_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            user_data = response.json()

            # Get user emails (primary email might not be in profile)
            emails_response = await client.get(
                self.EMAILS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            emails_response.raise_for_status()
            emails_data = emails_response.json()

        # Find primary verified email
        email = None
        email_verified = False
        for email_info in emails_data:
            if email_info.get("primary") and email_info.get("verified"):
                email = email_info["email"]
                email_verified = True
                break

        # Fallback to any verified email
        if not email:
            for email_info in emails_data:
                if email_info.get("verified"):
                    email = email_info["email"]
                    email_verified = True
                    break

        # Last resort: use email from profile (might be None)
        if not email:
            email = user_data.get("email")
            email_verified = False

        if not email:
            raise ValueError("No email found in GitHub account")

        return OAuthUserInfo(
            provider=self.name,
            provider_user_id=str(user_data["id"]),
            email=email,
            name=user_data.get("name") or user_data.get("login"),
            picture=user_data.get("avatar_url"),
            email_verified=email_verified,
        )
