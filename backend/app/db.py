"""
Camada de acesso ao Postgres.

Em MOCK_MODE não há conexão — os repositórios usam o seed em memória.
Em produção a senha do Postgres é resolvida nesta ordem:
  1. PGPASSWORD .............. senha estática (dev / Secrets Manager)
  2. RDS_IAM_AUTH=true ....... token IAM de curta duração (AWS RDS, via boto3)
  3. LAKEBASE_ENDPOINT ....... credencial OAuth do Databricks (Lakebase / Databricks Apps)

Deploy atual: Databricks Apps + Lakebase (caminho 3). Os caminhos AWS (1/2) ficam
disponíveis para um eventual host fora do Databricks.
"""
import logging
import time
from contextlib import contextmanager
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# cache da credencial de curta duração (Lakebase OAuth ~1h / RDS IAM ~15min).
_pw_cache: dict = {"token": None, "exp": 0.0}


def _db_password(s) -> Optional[str]:
    """Resolve a senha do Postgres conforme a estratégia configurada."""
    if s.PGPASSWORD:
        return s.PGPASSWORD

    now = time.time()
    if _pw_cache["token"] and _pw_cache["exp"] - now > 120:
        return _pw_cache["token"]

    # AWS RDS — token IAM via boto3
    if s.RDS_IAM_AUTH:
        import boto3
        client = boto3.client("rds", region_name=s.AWS_REGION)
        token = client.generate_db_auth_token(
            DBHostname=s.PGHOST, Port=s.PGPORT, DBUsername=s.PGUSER, Region=s.AWS_REGION,
        )
        _pw_cache["token"] = token
        _pw_cache["exp"] = now + 780          # 13 min
        return token

    # Databricks Lakebase (Database Instance) — credencial OAuth gerada pela
    # identidade do app (service principal) para a instância configurada.
    if s.LAKEBASE_INSTANCE_NAME:
        import uuid as _uuid
        from app.auth.workspace_client import get_workspace_client
        cred = get_workspace_client().database.generate_database_credential(
            request_id=str(_uuid.uuid4()),
            instance_names=[s.LAKEBASE_INSTANCE_NAME],
        )
        _pw_cache["token"] = cred.token
        _pw_cache["exp"] = now + 2700          # 45 min
        return cred.token

    return None


def _db_user(s) -> Optional[str]:
    """Usuário do Postgres. Com Lakebase OAuth (sem PGUSER explícito), a identidade
    é o service principal do app — o PG role é o client_id (DATABRICKS_CLIENT_ID)."""
    if s.PGUSER:
        return s.PGUSER
    if s.LAKEBASE_INSTANCE_NAME and s.DATABRICKS_CLIENT_ID:
        return s.DATABRICKS_CLIENT_ID
    return s.PGUSER


@contextmanager
def get_conn():
    """Conexão Postgres de curta duração (gera credencial fresca quando necessário)."""
    import psycopg

    s = get_settings()
    conn = psycopg.connect(
        host=s.PGHOST, port=s.PGPORT, dbname=s.PGDATABASE,
        user=_db_user(s), password=_db_password(s) or "",
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
        logger.warning(f"Postgres indisponível: {e}")
        return False
