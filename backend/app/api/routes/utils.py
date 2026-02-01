from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import SystemConfig

router = APIRouter(prefix="/utils", tags=["utils"])


class AppSettings(BaseModel):
    """Public application settings."""

    app_name: str
    support_email: str


@router.get("/health-check/")
async def health_check() -> bool:
    return True


@router.get("/app-settings/", response_model=AppSettings)
def get_app_settings(session: SessionDep) -> AppSettings:
    """
    Get public application settings.

    This endpoint is public and returns non-sensitive configuration
    like app name and support email.
    """
    # Get configs from DB
    configs = session.exec(
        select(SystemConfig).where(SystemConfig.key.in_(["app_name", "support_email"]))
    ).all()
    config_map = {c.key: c.value for c in configs}

    return AppSettings(
        app_name=config_map.get("app_name", settings.PROJECT_NAME),
        support_email=config_map.get(
            "support_email", settings.EMAILS_FROM_EMAIL or "support@example.com"
        ),
    )
