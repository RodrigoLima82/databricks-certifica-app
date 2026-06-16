"""
Segurança: hashing de senha (bcrypt) e tokens JWT.

Funciona em Databricks Apps e Azure App Service (independe da plataforma).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from app.config import get_settings
from app.models.schemas import UserPublic

logger = logging.getLogger(__name__)


# ── Senhas ────────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── JWT ─────────────────────────────────────────────────────────────────────
def create_token(email: str, must_change: bool = False) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=s.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": email.lower(), "exp": expire, "must_change": must_change},
        s.JWT_SECRET, algorithm="HS256",
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def _token_from_request(request: Request) -> Optional[str]:
    # Header customizado: o gateway do Databricks Apps usa/strip o Authorization
    # para o próprio OAuth, então o JWT do app trafega em X-App-Auth.
    x = request.headers.get("X-App-Auth", "")
    if x:
        return x[7:].strip() if x.startswith("Bearer ") else x.strip()
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def is_admin(email: str) -> bool:
    return bool(email) and email.lower() == get_settings().admin_email_norm


# ── Dependencies ──────────────────────────────────────────────────────────────
def get_current_user(request: Request) -> UserPublic:
    """Exige JWT válido. Usado nas rotas protegidas."""
    s = get_settings()
    if not s.ENABLE_JWT_AUTH:
        # auth desabilitado: usuário anônimo (dev)
        return UserPublic(email="anon@local", name="Anônimo", is_admin=True)

    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    email = payload["sub"]
    from app.services import users as users_svc
    user = users_svc.get_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return UserPublic(
        email=user["email"], name=user["name"],
        is_admin=is_admin(email),
        must_change_password=user.get("must_change_password", False),
    )


def require_admin(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito ao admin")
    return user
