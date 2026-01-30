import logging
from collections.abc import Generator
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import SMSDevice, TokenPayload, User
from app.services.qstash_service import QStashService

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_device_by_api_key(session: SessionDep, api_key: str) -> SMSDevice:
    """Validate api key and get the device"""

    device = crud.get_sms_device_by_api_key(session=session, api_key=api_key)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return device


def verify_device_active(device: SMSDevice) -> SMSDevice:
    """Verify that the device is active and online"""
    if device.status not in ["online", "idle"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not active",
        )
    return device


def get_current_device(
    session: SessionDep, api_key: Annotated[str, Depends(api_key_header)]
) -> SMSDevice:
    return get_device_by_api_key(session=session, api_key=api_key)


CurrentDevice = Annotated[SMSDevice, Depends(get_current_device)]


# Integration API Key authentication
integration_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_user_by_integration_api_key(
    session: SessionDep,
    api_key: Annotated[str | None, Depends(integration_api_key_header)],
) -> User | None:
    """Get user from integration API key (returns None if not provided or invalid)"""
    if not api_key:
        return None

    db_api_key = crud.get_api_key_by_key(session=session, key=api_key)
    if not db_api_key or not db_api_key.is_active:
        return None

    # Update last used timestamp
    crud.update_api_key_last_used(session=session, db_api_key=db_api_key)

    user = session.get(User, db_api_key.user_id)
    if not user or not user.is_active:
        return None

    return user


def get_current_user_or_integration(
    session: SessionDep,
    token: Annotated[
        str | None,
        Depends(
            OAuth2PasswordBearer(
                tokenUrl=f"{settings.API_V1_STR}/login/access-token", auto_error=False
            )
        ),
    ] = None,
    api_key: Annotated[str | None, Depends(integration_api_key_header)] = None,
) -> User:
    """
    Authenticate via JWT token OR integration API key.
    Allows endpoints to accept both authentication methods.
    """
    # Try API key first (for integrations)
    if api_key:
        db_api_key = crud.get_api_key_by_key(session=session, key=api_key)
        if db_api_key and db_api_key.is_active:
            crud.update_api_key_last_used(session=session, db_api_key=db_api_key)
            user = session.get(User, db_api_key.user_id)
            if user and user.is_active:
                return user

    # Try JWT token
    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
            )
            token_data = TokenPayload(**payload)
            user = session.get(User, token_data.sub)
            if user and user.is_active:
                return user
        except (InvalidTokenError, ValidationError):
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUserOrIntegration = Annotated[User, Depends(get_current_user_or_integration)]


async def get_verified_qstash_payload(request: Request) -> dict[str, Any]:
    """
    Verify QStash webhook signature and return parsed body.

    Raises HTTPException if signature is invalid.
    """
    signature = request.headers.get("Upstash-Signature", "")
    body = await request.body()

    if not QStashService.verify_signature(body, signature, str(request.url)):
        logger.warning("Invalid QStash signature received")
        raise HTTPException(status_code=401, detail="Invalid signature")

    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")

    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")


VerifiedQStashPayload = Annotated[dict[str, Any], Depends(get_verified_qstash_payload)]
