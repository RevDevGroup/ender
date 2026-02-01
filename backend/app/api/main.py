from fastapi import APIRouter

from app.api.routes import (
    api_keys,
    internal,
    login,
    oauth,
    plans,
    private,
    sms,
    subscriptions,
    system_config,
    users,
    utils,
    webhooks,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(sms.router)
api_router.include_router(plans.router)
api_router.include_router(webhooks.router)
api_router.include_router(api_keys.router)
api_router.include_router(oauth.router)
api_router.include_router(
    subscriptions.router, prefix="/subscriptions", tags=["subscriptions"]
)
api_router.include_router(internal.router, prefix="/internal", tags=["internal"])
api_router.include_router(system_config.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
