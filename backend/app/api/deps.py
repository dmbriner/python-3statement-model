from __future__ import annotations

from collections.abc import Generator
import json
from typing import Any
from urllib.request import urlopen

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _decode_clerk_token(token: str) -> dict[str, Any]:
    if not settings.clerk_jwt_issuer:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Clerk JWT issuer is not configured.")
    jwks_url = f"{settings.clerk_jwt_issuer.rstrip('/')}/.well-known/jwks.json"
    jwk_client = PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.clerk_jwt_issuer,
        options={"verify_aud": False},
    )


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = _decode_clerk_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.") from exc

    user_id = str(payload.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user payload.")

    email = payload.get("email")
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=email, auth_provider="clerk")
        db.add(user)
        db.commit()
        db.refresh(user)
    elif email and user.email != email:
        user.email = str(email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
