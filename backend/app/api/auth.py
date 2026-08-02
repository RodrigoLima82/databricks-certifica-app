"""
Endpoints de autenticação multi-tenant: registro, login, dados do usuário, troca de senha.
O tenant é resolvido pelo slug enviado no request (o front opera dentro de /t/{slug}).
"""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import get_settings
from app.models.schemas import (
    RegisterRequest, LoginRequest, ChangePasswordRequest, TokenResponse, UserPublic,
)
from app.auth import security
from app.services import users as users_svc, tenants as tenants_svc, activity

logger = logging.getLogger(__name__)
router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _resolve_tenant(slug: str) -> dict:
    t = tenants_svc.get_tenant_by_slug(slug)
    if not t or t.get("status") != "active":
        raise HTTPException(404, "Tenant não encontrado")
    return t


def _token_and_user(tenant: dict, email: str, name: str, is_admin: bool,
                    must_change: bool) -> TokenResponse:
    # superadmin = pertence ao tenant 'platform' (ou está em SUPERADMIN_EMAILS, bootstrap)
    sa = security.is_superadmin(email) or tenant["slug"] == get_settings().PLATFORM_TENANT_SLUG
    token = security.create_token(email, name, tenant["id"], tenant["slug"],
                                  is_admin=is_admin, is_superadmin=sa, must_change=must_change)
    user = UserPublic(email=email.lower(), name=name, tenant_id=tenant["id"],
                      tenant_slug=tenant["slug"], is_admin=is_admin, is_superadmin=sa,
                      must_change_password=must_change)
    return TokenResponse(access_token=token, user=user)


@router.get("/status")
async def status():
    s = get_settings()
    return {"auth_enabled": s.ENABLE_JWT_AUTH, "pass_mark": s.PASS_MARK}


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, request: Request):
    tenant = _resolve_tenant(data.tenant_slug)
    if not tenant.get("allow_self_register"):
        raise HTTPException(403, "Auto-registro desabilitado neste tenant.")
    email = data.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(422, "E-mail inválido")
    if len(data.password) < 6:
        raise HTTPException(422, "A senha deve ter ao menos 6 caracteres")
    if not data.name.strip():
        raise HTTPException(422, "Nome obrigatório")
    if users_svc.get_user(tenant["id"], email):
        raise HTTPException(409, "E-mail já cadastrado neste tenant. Faça login.")

    users_svc.create_user(tenant["id"], email, data.name.strip(),
                          security.hash_password(data.password), is_admin=False)
    activity.log_event(tenant["id"], email, "register", request=request,
                       user_name=data.name.strip())
    return _token_and_user(tenant, email, data.name.strip(), is_admin=False, must_change=False)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request):
    tenant = _resolve_tenant(data.tenant_slug)
    email = data.email.strip().lower()
    user = users_svc.get_user(tenant["id"], email)
    if not user or not security.verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "E-mail ou senha incorretos")
    if user.get("status") == "suspended":
        raise HTTPException(403, "Usuário suspenso. Contate o administrador.")
    activity.log_event(tenant["id"], email, "login", request=request,
                       user_name=user["name"],
                       detail={"is_admin": bool(user.get("is_admin"))})
    return _token_and_user(tenant, email, user["name"],
                           is_admin=bool(user.get("is_admin")),
                           must_change=user.get("must_change_password", False))


@router.get("/me", response_model=UserPublic)
async def me(user: UserPublic = Depends(security.get_current_user)):
    return user


@router.post("/change-password", response_model=TokenResponse)
async def change_password(data: ChangePasswordRequest, request: Request,
                          user: UserPublic = Depends(security.get_current_user)):
    if len(data.new_password) < 6:
        raise HTTPException(422, "A senha deve ter ao menos 6 caracteres")
    users_svc.update_password(user.tenant_id, user.email,
                              security.hash_password(data.new_password))
    activity.log_event(user.tenant_id, user.email, "password_change", request=request,
                       user_name=user.name)
    token = security.create_token(user.email, user.name, user.tenant_id, user.tenant_slug,
                                  is_admin=user.is_admin, is_superadmin=user.is_superadmin,
                                  must_change=False)
    return TokenResponse(access_token=token,
                         user=user.model_copy(update={"must_change_password": False}))
