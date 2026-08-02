"""
CRUD de usuários — escopado por tenant (PK lógica: tenant_id + email).
Postgres em produção, dict em memória no MOCK_MODE.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# store em memória para dev (MOCK_MODE): chave (tenant_id, email)
_mem: dict[tuple, dict] = {}


def _use_db() -> bool:
    return not get_settings().MOCK_MODE


def get_user(tenant_id: str, email: str) -> Optional[dict]:
    email = email.lower()
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            r = conn.execute(
                "SELECT email,name,password_hash,must_change_password,is_admin,status,area "
                "FROM users WHERE tenant_id=%s AND email=%s", (tenant_id, email)
            ).fetchone()
        if not r:
            return None
        return {"email": r[0], "name": r[1], "password_hash": r[2],
                "must_change_password": r[3], "is_admin": r[4],
                "status": r[5] or "active", "area": r[6]}
    return _mem.get((tenant_id, email))


def create_user(tenant_id: str, email: str, name: str, password_hash: str,
                is_admin: bool = False, must_change_password: bool = False,
                area: Optional[str] = None) -> dict:
    email = email.lower()
    rec = {"email": email, "name": name, "password_hash": password_hash,
           "is_admin": is_admin, "must_change_password": must_change_password,
           "status": "active", "area": area}
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (tenant_id,email,name,password_hash,is_admin,"
                "must_change_password,area) VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (tenant_id,email) DO NOTHING",
                (tenant_id, email, name, password_hash, is_admin, must_change_password, area),
            )
    else:
        _mem.setdefault((tenant_id, email), rec)
    return rec


def update_password(tenant_id: str, email: str, password_hash: str) -> None:
    email = email.lower()
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET password_hash=%s, must_change_password=FALSE "
                "WHERE tenant_id=%s AND email=%s", (password_hash, tenant_id, email),
            )
    elif (tenant_id, email) in _mem:
        _mem[(tenant_id, email)]["password_hash"] = password_hash
        _mem[(tenant_id, email)]["must_change_password"] = False


# ── Gestão pelo admin do tenant ────────────────────────────────────────────────
def update_profile(tenant_id: str, email: str, name: Optional[str], area: Optional[str]) -> None:
    email = email.lower()
    if _use_db():
        from app.db import get_conn
        sets, params = [], []
        if name is not None:
            sets.append("name=%s"); params.append(name)
        if area is not None:
            sets.append("area=%s"); params.append(area)
        if not sets:
            return
        params += [tenant_id, email]
        with get_conn() as conn:
            conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE tenant_id=%s AND email=%s", params)
    elif (tenant_id, email) in _mem:
        if name is not None: _mem[(tenant_id, email)]["name"] = name
        if area is not None: _mem[(tenant_id, email)]["area"] = area


def set_status(tenant_id: str, email: str, status: str) -> None:
    email = email.lower()
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            conn.execute("UPDATE users SET status=%s WHERE tenant_id=%s AND email=%s",
                         (status, tenant_id, email))
    elif (tenant_id, email) in _mem:
        _mem[(tenant_id, email)]["status"] = status


def list_users(tenant_id: str) -> list[dict]:
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT email,name,is_admin,status,area,created_at FROM users "
                "WHERE tenant_id=%s ORDER BY name", (tenant_id,)
            ).fetchall()
        return [{"email": r[0], "name": r[1], "is_admin": r[2], "status": r[3] or "active",
                 "area": r[4], "created_at": r[5].isoformat() if r[5] else None} for r in rows]
    return [{"email": v["email"], "name": v["name"], "is_admin": v.get("is_admin", False),
             "status": v.get("status", "active"), "area": v.get("area"), "created_at": None}
            for k, v in _mem.items() if k[0] == tenant_id]


def delete_user(tenant_id: str, email: str) -> None:
    email = email.lower()
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            # remove tentativas do usuário e depois o usuário
            conn.execute("DELETE FROM test_answers WHERE tenant_id=%s AND session_id IN "
                         "(SELECT id FROM test_sessions WHERE tenant_id=%s AND user_email=%s)",
                         (tenant_id, tenant_id, email))
            conn.execute("DELETE FROM test_sessions WHERE tenant_id=%s AND user_email=%s",
                         (tenant_id, email))
            conn.execute("DELETE FROM users WHERE tenant_id=%s AND email=%s", (tenant_id, email))
    else:
        _mem.pop((tenant_id, email), None)
