from beanie import init_beanie
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api.users import auth_backend, fastapi_users
from app.database.database import db
from app.models.models import Message, User
from app.routes import index, messages
from app.schemas.schemas import UserCreate, UserRead, UserUpdate

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
    fastapi_users.get_auth_router(
        auth_backend, requires_verification=False
    ),  # Set requires_verification True in a future
    prefix="/auth/jwt",
    tags=["Auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(
    fastapi_users.get_users_router(
        UserRead, UserUpdate, requires_verification=False
    ),  # Set requires_verification True in a future
    prefix="/users",
    tags=["Users"],
)
app.include_router(messages.router)


@app.on_event("startup")
async def on_startup():
    await init_beanie(
        database=db,
        document_models=[User, Message],
    )
