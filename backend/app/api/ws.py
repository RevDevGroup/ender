from fastapi import APIRouter

from app.api.routes.android import router as android_ws_router

ws_router = APIRouter()
ws_router.include_router(android_ws_router)
