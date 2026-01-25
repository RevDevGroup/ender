import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ApiKeyCreate,
    ApiKeyCreatePublic,
    ApiKeyPublic,
    ApiKeysPublic,
    Message,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreatePublic,
)
def create_api_key(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    api_key_in: ApiKeyCreate,
) -> ApiKeyCreatePublic:
    """Generate a new API key for integrations"""
    api_key = crud.create_api_key(
        session=session, api_key_in=api_key_in, user_id=current_user.id
    )
    return ApiKeyCreatePublic(
        id=api_key.id,
        name=api_key.name,
        key=api_key.key,
        created_at=api_key.created_at,
    )


@router.get("", response_model=ApiKeysPublic)
def list_api_keys(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> ApiKeysPublic:
    """List all API keys for the current user"""
    api_keys = crud.get_api_keys_by_user(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return ApiKeysPublic(
        data=[
            ApiKeyPublic(
                id=k.id,
                name=k.name,
                is_active=k.is_active,
                key_prefix=k.key[:12] + "...",
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in api_keys
        ],
        count=len(api_keys),
    )


@router.post("/{api_key_id}/revoke", response_model=Message)
def revoke_api_key(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    api_key_id: uuid.UUID,
) -> Message:
    """Revoke an API key (deactivate without deleting)"""
    api_key = crud.get_api_key(session=session, api_key_id=api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="API key already revoked"
        )
    crud.revoke_api_key(session=session, db_api_key=api_key)
    return Message(message="API key revoked")


@router.delete("/{api_key_id}", response_model=Message)
def delete_api_key(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    api_key_id: uuid.UUID,
) -> Message:
    """Delete an API key permanently"""
    api_key = crud.get_api_key(session=session, api_key_id=api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    crud.delete_api_key(session=session, api_key_id=api_key_id)
    return Message(message="API key deleted")
