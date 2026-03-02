from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, companies, exports, persistence

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(persistence.router, prefix="/me", tags=["persistence"])
