"""
Log de acessos e atividades — auditoria por tenant para o admin.

Registra eventos (login, troca de senha, submissão de simulado, geração via IA,
conclusão de aula, etc.) de forma *best-effort*: uma falha ao gravar o log NUNCA
quebra a requisição de negócio (o registro é envolto em try/except).

Escopo por tenant_id (mesmo isolamento row-level das demais tabelas).
"""
import json
import logging
import uuid
from typing import List, Optional

from fastapi import Request

from app.config import get_settings

logger = logging.getLogger(__name__)


def _use_db() -> bool:
    return not get_settings().MOCK_MODE


def _client_meta(request: Optional[Request]) -> tuple:
    """Extrai IP e User-Agent do request (tolerante a proxies do Databricks Apps).

    Nota: x-forwarded-for é spoofável pelo cliente; serve como pista de auditoria
    (soft audit), não como prova forense. O gateway do Databricks Apps normalmente
    injeta o IP real, mas não confie nele para decisões de segurança.
    """
    if request is None:
        return None, None
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    ua = request.headers.get("user-agent")
    return ip, (ua[:400] if ua else None)


def log_event(tenant_id: Optional[str], user_email: str, action: str,
              detail: Optional[dict] = None, request: Optional[Request] = None,
              user_name: Optional[str] = None) -> None:
    """Grava um evento de atividade. Best-effort: erros são apenas logados."""
    if not _use_db() or not tenant_id or not user_email:
        return
    try:
        ip, ua = _client_meta(request)
        from app.db import get_conn
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO activity_log (id,tenant_id,user_email,user_name,action,detail,ip,user_agent) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, user_email.lower(), user_name, action,
                 json.dumps(detail or {}), ip, ua),
            )
    except Exception as e:  # nunca quebra a requisição de negócio
        logger.warning(f"activity.log_event falhou ({action}): {e}")


def get_activity(tenant_id: str, limit: int = 200, email: Optional[str] = None,
                 action: Optional[str] = None) -> List[dict]:
    """Lista eventos do tenant (mais recentes primeiro), com filtros opcionais."""
    if not _use_db():
        return []
    from app.db import get_conn
    sql = ("SELECT id,user_email,user_name,action,detail,ip,user_agent,created_at "
           "FROM activity_log WHERE tenant_id=%s")
    params: list = [tenant_id]
    if email:
        sql += " AND user_email=%s"
        params.append(email.lower())
    if action:
        sql += " AND action=%s"
        params.append(action)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(min(max(limit, 1), 2000))
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    def _j(v):
        if v is None:
            return {}
        return v if isinstance(v, dict) else json.loads(v)

    return [{
        "id": r[0], "user_email": r[1], "user_name": r[2], "action": r[3],
        "detail": _j(r[4]), "ip": r[5], "user_agent": r[6],
        "created_at": r[7].isoformat() if r[7] else None,
    } for r in rows]


def activity_summary(tenant_id: str) -> dict:
    """KPIs rápidos: total de eventos, logins (7d) e usuários ativos (7d)."""
    if not _use_db():
        return {"total_events": 0, "logins_7d": 0, "active_users_7d": 0}
    from app.db import get_conn
    with get_conn() as conn:
        r = conn.execute(
            "SELECT COUNT(*), "
            "  COUNT(*) FILTER (WHERE action='login' AND created_at >= now() - interval '7 days'), "
            "  COUNT(DISTINCT user_email) FILTER (WHERE created_at >= now() - interval '7 days') "
            "FROM activity_log WHERE tenant_id=%s", (tenant_id,),
        ).fetchone()
    return {"total_events": r[0] or 0, "logins_7d": r[1] or 0, "active_users_7d": r[2] or 0}
