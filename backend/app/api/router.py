from fastapi import APIRouter

router = APIRouter()

from app.api.endpoints import auth, claims, chat

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(claims.router, prefix="/claims", tags=["claims"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
