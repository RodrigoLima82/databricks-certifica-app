"""
Camada de acesso ao Lakebase (Postgres).

Em MOCK_MODE não há conexão — os repositórios usam o seed em memória.
Em produção, a senha é uma credencial OAuth de curta duração gerada pela
WorkspaceClient para a instância Lakebase (ou PGPASSWORD, se fornecido).
"""
import logging
import time
from contextlib import contextmanager
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

_password_cache: dict = {"token": None, "exp": 0.0}


def _lakebase_password(s) -> Optional[str]:
    """Senha do Postgres: PGPASSWORD direto ou credencial OAuth do endpoint Lakebase Autoscaling."""
    if s.PGPASSWORD:
        return s.PGPASSWORD
    if not s.LAKEBASE_ENDPOINT:
        return None

    now = time.time()
    if _password_cache["token"] and _password_cache["exp"] - now > 120:
        return _password_cache["token"]

    from app.auth.workspace_client import get_workspace_client

    client = get_workspace_client()
    cred = client.postgres.generate_database_credential(endpoint=s.LAKEBASE_ENDPOINT)
    # token Lakebase válido por ~1h; renova com folga (45 min)
    _password_cache["token"] = cred.token
    _password_cache["exp"] = now + 2700
    return cred.token


@contextmanager
def get_conn():
    """Conexão Postgres de curta duração (gera credencial fresca quando necessário)."""
    import psycopg

    s = get_settings()
    conn = psycopg.connect(
        host=s.PGHOST, port=s.PGPORT, dbname=s.PGDATABASE,
        user=s.PGUSER, password=_lakebase_password(s) or "",
        sslmode=s.PGSSLMODE, options=f"-c search_path={s.PGSCHEMA}",
        autocommit=True, connect_timeout=15,
    )
    try:
        yield conn
    finally:
        conn.close()


def is_db_ready() -> bool:
    s = get_settings()
    if s.MOCK_MODE:
        return False
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:  # pragma: no cover
        logger.warning(f"Lakebase indisponível: {e}")
        return False
