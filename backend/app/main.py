import logging
from contextlib import asynccontextmanager

import sentry_sdk
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.fcm_service import FCMService
from app.services.notification_dispatcher import NotificationDispatcher
from app.services.qstash_service import QStashService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


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


def rate_limit_exceeded_handler(
    request: Request,  # noqa: ARG001 - Required by FastAPI exception handler
    exc: RateLimitExceeded,
):
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": exc.detail,
        },
        headers={"Retry-After": str(exc.detail)},
    )


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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
