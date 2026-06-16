"""
CRUD de usuários — Lakebase (Postgres) em produção, dict em memória no MOCK_MODE.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# store em memória para dev/testes (MOCK_MODE)
_mem: dict[str, dict] = {}


def _use_db() -> bool:
    return not get_settings().MOCK_MODE


def get_user(email: str) -> Optional[dict]:
    email = email.lower()
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            r = conn.execute(
                "SELECT email,name,password_hash,must_change_password "
                "FROM users WHERE email=%s", (email,)
            ).fetchone()
        if not r:
            return None
        return {"email": r[0], "name": r[1], "password_hash": r[2],
                "must_change_password": r[3]}
    return _mem.get(email)


def create_user(email: str, name: str, password_hash: str,
                must_change_password: bool = False) -> dict:
    email = email.lower()
    rec = {"email": email, "name": name, "password_hash": password_hash,
           "must_change_password": must_change_password}
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (email,name,password_hash,must_change_password) "
                "VALUES (%s,%s,%s,%s) ON CONFLICT (email) DO NOTHING",
                (email, name, password_hash, must_change_password),
            )
    else:
        _mem.setdefault(email, rec)
    return rec


def update_password(email: str, password_hash: str) -> None:
    email = email.lower()
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET password_hash=%s, must_change_password=FALSE "
                "WHERE email=%s", (password_hash, email),
            )
    elif email in _mem:
        _mem[email]["password_hash"] = password_hash
        _mem[email]["must_change_password"] = False


def list_users() -> list[dict]:
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            rows = conn.execute("SELECT email,name FROM users ORDER BY name").fetchall()
        return [{"email": r[0], "name": r[1]} for r in rows]
    return [{"email": u["email"], "name": u["name"]} for u in _mem.values()]


def seed_provisioned_users() -> None:
    """Cria usuários pré-provisionados (env PROVISIONED_USERS) no startup."""
    s = get_settings()
    if not s.provisioned_users_list:
        return
    if not s.PROVISIONED_INITIAL_PASSWORD:
        logger.warning("PROVISIONED_USERS definido, mas PROVISIONED_INITIAL_PASSWORD vazio — "
                       "defina a senha inicial via env. Pulando provisionamento.")
        return
    from app.auth.security import hash_password
    pw = hash_password(s.PROVISIONED_INITIAL_PASSWORD)
    for email in s.provisioned_users_list:
        if not get_user(email):
            name = email.split("@")[0].replace(".", " ").title()
            create_user(email, name, pw, must_change_password=True)
            logger.info(f"Usuário provisionado: {email}")
