from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models import User

router = APIRouter()


@router.get("/config")
def auth_config() -> dict[str, str | bool]:
    return {
        "provider": settings.auth_provider,
        "clerk_publishable_key": settings.clerk_publishable_key or "",
        "auth_required": True,
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, str | None]:
    return {"id": user.id, "email": user.email, "auth_provider": user.auth_provider}
