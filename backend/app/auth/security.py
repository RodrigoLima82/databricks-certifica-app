"""
Segurança: hashing de senha (bcrypt) e tokens JWT (multi-tenant).

O JWT carrega o tenant (tid/tslug) e os papéis (adm = admin do tenant,
sa = superadmin da plataforma). É stateless: o contexto de tenant viaja no token.
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


def is_superadmin(email: str) -> bool:
    return bool(email) and email.lower() in get_settings().superadmin_emails_list


# ── JWT ─────────────────────────────────────────────────────────────────────
def create_token(email: str, name: str, tenant_id: Optional[str], tenant_slug: Optional[str],
                 is_admin: bool = False, is_superadmin: bool = False,
                 must_change: bool = False) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=s.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": email.lower(), "nm": name, "tid": tenant_id, "tslug": tenant_slug,
         "adm": is_admin, "sa": is_superadmin, "must_change": must_change, "exp": expire},
        s.JWT_SECRET, algorithm="HS256",
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def _token_from_request(request: Request) -> Optional[str]:
    # O gateway do Databricks Apps consome o Authorization para o próprio OAuth,
    # então o JWT do app trafega num header customizado (AUTH_HEADER, configurável).
    x = request.headers.get(get_settings().AUTH_HEADER, "")
    if x:
        return x[7:].strip() if x.startswith("Bearer ") else x.strip()
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


# ── Dependencies ──────────────────────────────────────────────────────────────
def get_current_user(request: Request) -> UserPublic:
    """Exige JWT válido. O contexto de tenant vem do próprio token."""
    s = get_settings()
    if not s.ENABLE_JWT_AUTH:
        return UserPublic(email="anon@local", name="Anônimo", tenant_id=None,
                          is_admin=True, is_superadmin=True)

    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    p = decode_token(token)
    if not p or not p.get("sub"):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return UserPublic(
        email=p["sub"], name=p.get("nm") or p["sub"], tenant_id=p.get("tid"),
        tenant_slug=p.get("tslug"), is_admin=bool(p.get("adm")),
        is_superadmin=bool(p.get("sa")), must_change_password=bool(p.get("must_change")),
    )


def require_admin(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if not (user.is_admin or user.is_superadmin):
        raise HTTPException(status_code=403, detail="Acesso restrito ao admin")
    return user


def require_superadmin(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Acesso restrito à plataforma")
    return user
