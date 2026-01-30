from contextlib import asynccontextmanager

import sentry_sdk
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.services.fcm_service import FCMService
from app.services.notification_dispatcher import NotificationDispatcher
from app.services.qstash_service import QStashService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Run migrations on startup
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    # Initialize services
    FCMService.initialize()
    QStashService.initialize()
    NotificationDispatcher.initialize()

    yield


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
