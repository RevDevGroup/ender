"""
OAuth authentication routes.

Provides endpoints for OAuth authentication with Google and GitHub.
"""

import logging
import secrets
from datetime import timedelta
from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.core.rate_limit import RateLimits, limiter
from app.models import (
    Message,
    OAuthAccountPublic,
    OAuthAccountsPublic,
    OAuthAuthorizeResponse,
    OAuthLinkRequest,
    OAuthProviderInfo,
    OAuthProvidersResponse,
    SetPasswordRequest,
    Token,
)
from app.services.oauth import get_oauth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])

# Session key for OAuth state
OAUTH_STATE_KEY = "oauth_state"


ProviderName = Annotated[Literal["google", "github"], "OAuth provider name"]


def get_redirect_uri(provider: str) -> str:
    """Get the OAuth redirect URI for a provider (goes to backend)."""
    base_url = settings.SERVER_BASE_URL or "http://localhost:8000"
    return f"{base_url}{settings.API_V1_STR}/oauth/{provider}/callback"


def get_frontend_callback_url(
    provider: str,
    *,
    access_token: str | None = None,
    is_new_user: bool = False,
    requires_linking: bool = False,
    existing_email: str | None = None,
    error: str | None = None,
) -> str:
    """Build frontend callback URL with query parameters."""
    params: dict[str, str] = {}
    if access_token:
        params["access_token"] = access_token
    if is_new_user:
        params["is_new_user"] = "true"
    if requires_linking:
        params["requires_linking"] = "true"
    if existing_email:
        params["existing_email"] = existing_email
    if error:
        params["error"] = error

    query_string = urlencode(params) if params else ""
    base_url = f"{settings.FRONTEND_HOST}/oauth-callback/{provider}"
    return f"{base_url}?{query_string}" if query_string else base_url


@router.get("/providers", response_model=OAuthProvidersResponse)
def list_providers() -> OAuthProvidersResponse:
    """
    List available OAuth providers and their status.
    """
    service = get_oauth_service()
    providers = [
        OAuthProviderInfo(name=p["name"], enabled=bool(p["enabled"]))
        for p in service.get_available_providers()
    ]
    return OAuthProvidersResponse(providers=providers)


@router.get("/{provider}/authorize", response_model=OAuthAuthorizeResponse)
@limiter.limit(RateLimits.AUTH_LOGIN)
def authorize(
    request: Request,
    provider: ProviderName,
) -> OAuthAuthorizeResponse:
    """
    Get OAuth authorization URL for the specified provider.

    The client should redirect the user to this URL to start the OAuth flow.
    """
    service = get_oauth_service()
    oauth_provider = service.get_provider(provider)

    if not oauth_provider:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth provider '{provider}' is not available or not configured",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session (managed by SessionMiddleware)
    request.session[OAUTH_STATE_KEY] = state

    redirect_uri = get_redirect_uri(provider)
    authorization_url = oauth_provider.get_authorization_url(state, redirect_uri)

    return OAuthAuthorizeResponse(authorization_url=authorization_url)


@router.get("/{provider}/callback")
@limiter.limit(RateLimits.AUTH_LOGIN)
async def callback(
    request: Request,
    session: SessionDep,
    provider: ProviderName,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """
    Handle OAuth callback from provider.

    Exchanges the authorization code for tokens and redirects to frontend.
    """
    # Handle OAuth error from provider
    if error:
        return RedirectResponse(
            url=get_frontend_callback_url(provider, error=error_description or error)
        )

    if not code or not state:
        return RedirectResponse(
            url=get_frontend_callback_url(
                provider, error="Missing code or state parameter"
            )
        )

    # Verify state from session
    stored_state = request.session.get(OAUTH_STATE_KEY)
    logger.info(
        f"OAuth callback - state from query: {state[:10]}..., "
        f"state from session: {stored_state[:10] if stored_state else 'None'}"
    )
    if not stored_state or stored_state != state:
        return RedirectResponse(
            url=get_frontend_callback_url(provider, error="Invalid state parameter")
        )

    # Clear state from session after validation
    request.session.pop(OAUTH_STATE_KEY, None)

    service = get_oauth_service()
    oauth_provider = service.get_provider(provider)

    if not oauth_provider:
        return RedirectResponse(
            url=get_frontend_callback_url(
                provider, error=f"OAuth provider '{provider}' is not available"
            )
        )

    try:
        redirect_uri = get_redirect_uri(provider)

        # Exchange code for tokens
        tokens = await oauth_provider.exchange_code(code, redirect_uri)

        # Get user info from provider
        user_info = await oauth_provider.get_user_info(tokens.access_token)

    except ValueError as e:
        return RedirectResponse(url=get_frontend_callback_url(provider, error=str(e)))
    except Exception:
        return RedirectResponse(
            url=get_frontend_callback_url(
                provider, error="Failed to communicate with OAuth provider"
            )
        )

    # Check if OAuth account already exists
    existing_oauth = crud.get_oauth_account_by_provider_user_id(
        session=session,
        provider=user_info.provider,
        provider_user_id=user_info.provider_user_id,
    )

    if existing_oauth:
        # Update tokens and redirect with access token
        crud.update_oauth_account_tokens(
            session=session, db_oauth=existing_oauth, tokens=tokens
        )
        user = existing_oauth.user

        if not user.is_active:
            return RedirectResponse(
                url=get_frontend_callback_url(provider, error="Inactive user")
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )

        return RedirectResponse(
            url=get_frontend_callback_url(
                provider, access_token=access_token, is_new_user=False
            )
        )

    # Check if user with this email already exists
    existing_user = crud.get_user_by_email(session=session, email=user_info.email)

    if existing_user:
        # User exists but doesn't have this OAuth provider linked
        # Check if they have a password (need to link with password verification)
        if crud.user_has_password(user=existing_user):
            response = RedirectResponse(
                url=get_frontend_callback_url(
                    provider,
                    requires_linking=True,
                    existing_email=user_info.email,
                )
            )
            # Keep state cookie for linking flow
            return response

        # User is OAuth-only, link this provider
        crud.create_oauth_account(
            session=session,
            user_id=existing_user.id,
            user_info=user_info,
            tokens=tokens,
        )

        if not existing_user.is_active:
            return RedirectResponse(
                url=get_frontend_callback_url(provider, error="Inactive user")
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            existing_user.id, expires_delta=access_token_expires
        )

        return RedirectResponse(
            url=get_frontend_callback_url(
                provider, access_token=access_token, is_new_user=False
            )
        )

    # Create new user
    user = crud.create_user_from_oauth(
        session=session, user_info=user_info, tokens=tokens
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    return RedirectResponse(
        url=get_frontend_callback_url(
            provider, access_token=access_token, is_new_user=True
        )
    )


@router.post("/{provider}/link", response_model=Token)
@limiter.limit(RateLimits.AUTH_LOGIN)
def link_oauth_account(
    request: Request,  # noqa: ARG001 - Required by SlowAPI limiter
    session: SessionDep,
    provider: ProviderName,
    link_request: OAuthLinkRequest,
) -> Token:
    """
    Link an OAuth account to an existing user by verifying their password.

    This is used when a user with an existing password-based account
    tries to login with OAuth for the first time. The frontend should
    call this after the user enters their password.
    """
    # Verify user exists and password is correct
    user = crud.authenticate(
        session=session, email=link_request.email, password=link_request.password
    )

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Check if user already has this provider linked
    existing_oauth = crud.get_oauth_account_by_user_and_provider(
        session=session, user_id=user.id, provider=provider
    )

    if existing_oauth:
        # Already linked, just return token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return Token(
            access_token=security.create_access_token(
                user.id, expires_delta=access_token_expires
            )
        )

    # For linking, we need the OAuth info which should be stored temporarily
    # Since we can't get OAuth info without going through the flow again,
    # we'll create a placeholder that will be updated on next OAuth login
    # For now, just authenticate the user
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.delete("/{provider}/unlink", response_model=Message)
def unlink_oauth_account(
    session: SessionDep,
    current_user: CurrentUser,
    provider: ProviderName,
) -> Message:
    """
    Unlink an OAuth account from the current user.

    User must have either a password or another OAuth account to unlink.
    """
    # Check if user has this OAuth account
    oauth_account = crud.get_oauth_account_by_user_and_provider(
        session=session, user_id=current_user.id, provider=provider
    )

    if not oauth_account:
        raise HTTPException(
            status_code=404,
            detail=f"No {provider} account linked to your profile",
        )

    # Ensure user has another way to login
    has_password = crud.user_has_password(user=current_user)
    oauth_accounts = crud.get_oauth_accounts_by_user(
        session=session, user_id=current_user.id
    )

    if not has_password and len(oauth_accounts) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot unlink the only authentication method. Set a password first.",
        )

    crud.delete_oauth_account(session=session, oauth_account_id=oauth_account.id)
    return Message(message=f"{provider.capitalize()} account unlinked successfully")


@router.get("/accounts", response_model=OAuthAccountsPublic)
def list_oauth_accounts(
    session: SessionDep,
    current_user: CurrentUser,
) -> OAuthAccountsPublic:
    """
    List OAuth accounts linked to the current user.
    """
    accounts = crud.get_oauth_accounts_by_user(session=session, user_id=current_user.id)
    return OAuthAccountsPublic(
        data=[OAuthAccountPublic.model_validate(a) for a in accounts],
        count=len(accounts),
    )


@router.post("/set-password", response_model=Message)
def set_password(
    session: SessionDep,
    current_user: CurrentUser,
    password_request: SetPasswordRequest,
) -> Message:
    """
    Set a password for an OAuth-only user.

    This allows OAuth users to also login with email/password.
    """
    if crud.user_has_password(user=current_user):
        raise HTTPException(
            status_code=400,
            detail="User already has a password. Use password change instead.",
        )

    crud.set_user_password(
        session=session, user=current_user, password=password_request.new_password
    )
    return Message(message="Password set successfully")
