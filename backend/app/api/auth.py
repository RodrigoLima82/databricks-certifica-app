"""
Endpoints de autenticação: registro, login, dados do usuário, troca de senha.
"""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.models.schemas import (
    RegisterRequest, LoginRequest, ChangePasswordRequest, TokenResponse, UserPublic,
)
from app.auth import security
from app.services import users as users_svc

logger = logging.getLogger(__name__)
router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _public(email: str, name: str, must_change: bool) -> UserPublic:
    return UserPublic(email=email.lower(), name=name,
                      is_admin=security.is_admin(email),
                      must_change_password=must_change)


@router.get("/status")
async def status():
    s = get_settings()
    return {"auth_enabled": s.ENABLE_JWT_AUTH, "allow_self_register": s.ALLOW_SELF_REGISTER,
            "pass_mark": s.PASS_MARK}


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest):
    s = get_settings()
    if not s.ALLOW_SELF_REGISTER:
        raise HTTPException(403, "Auto-registro desabilitado. Contate o admin.")
    email = data.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(422, "E-mail inválido")
    if len(data.password) < 6:
        raise HTTPException(422, "A senha deve ter ao menos 6 caracteres")
    if not data.name.strip():
        raise HTTPException(422, "Nome obrigatório")
    if users_svc.get_user(email):
        raise HTTPException(409, "E-mail já cadastrado. Faça login.")

    users_svc.create_user(email, data.name.strip(),
                          security.hash_password(data.password))
    token = security.create_token(email, must_change=False)
    return TokenResponse(access_token=token, user=_public(email, data.name.strip(), False))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    email = data.email.strip().lower()
    user = users_svc.get_user(email)
    if not user or not security.verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "E-mail ou senha incorretos")
    must_change = user.get("must_change_password", False)
    token = security.create_token(email, must_change=must_change)
    return TokenResponse(access_token=token,
                         user=_public(email, user["name"], must_change))


@router.get("/me", response_model=UserPublic)
async def me(user: UserPublic = Depends(security.get_current_user)):
    return user


@router.post("/change-password", response_model=TokenResponse)
async def change_password(data: ChangePasswordRequest,
                          user: UserPublic = Depends(security.get_current_user)):
    if len(data.new_password) < 6:
        raise HTTPException(422, "A senha deve ter ao menos 6 caracteres")
    users_svc.update_password(user.email, security.hash_password(data.new_password))
    token = security.create_token(user.email, must_change=False)
    return TokenResponse(access_token=token,
                         user=_public(user.email, user.name, False))
