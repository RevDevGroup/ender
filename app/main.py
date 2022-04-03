from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from app.api.users import auth_backend, fastapi_users
from app.core.config import DATABASE_URL
from app.routes import index, messages

app = FastAPI(
    version="0.1.0",
    title="SMS Gateway API",
    description="SMS Gateway API using the ISP Etecsa",
    contact={
        "name": "RevDev Support",
        "url": "https://revdev.cc/support",
        "email": "revdev@protonmail.com",
    },
    license={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(index.router)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["Auth"]
)
app.include_router(fastapi_users.get_register_router(), prefix="/auth", tags=["Auth"])
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(
    fastapi_users.get_verify_router(),
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(fastapi_users.get_users_router(), prefix="/users", tags=["Users"])
app.include_router(messages.router)

register_tortoise(
    app,
    db_url=DATABASE_URL,
    modules={"models": ["app.models.models"]},
    generate_schemas=True,
)
