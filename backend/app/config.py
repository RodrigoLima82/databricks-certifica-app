"""
Certifica — Configurações da aplicação.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Certifica"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Marca / white-label (tudo configurável por env; nada hardcoded) ────────
    # Header HTTP onde o JWT do app trafega (o gateway do Databricks Apps consome
    # o Authorization para o próprio OAuth). Neutro por padrão.
    AUTH_HEADER: str = "X-App-Auth"
    # Primeiro tenant (cliente) criado no seed. Vazio = só cria o tenant interno
    # 'platform' (a empresa cria o próprio espaço via /signup ou consola).
    DEFAULT_TENANT_SLUG: str = ""
    DEFAULT_TENANT_NAME: str = ""
    DEFAULT_TENANT_COLOR: str = "#2272B4"      # azul neutro (override por tenant)
    DEFAULT_TENANT_LOGO: str = ""

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8005

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3006"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # ── Databricks (injetado automaticamente em Databricks Apps) ──────────────
    DATABRICKS_HOST: str = ""
    DATABRICKS_TOKEN: Optional[str] = None
    DATABRICKS_CLIENT_ID: Optional[str] = None
    DATABRICKS_CLIENT_SECRET: Optional[str] = None

    @property
    def databricks_host(self) -> str:
        h = self.DATABRICKS_HOST
        if h and not h.startswith("http"):
            h = f"https://{h}"
        return h

    # ── Postgres (Databricks Lakebase | AWS RDS) ──────────────────────────────
    # Lakebase (deploy atual): a senha é uma credencial OAuth gerada em runtime
    # para LAKEBASE_INSTANCE_NAME com a identidade do app (service principal).
    LAKEBASE_INSTANCE_NAME: Optional[str] = None
    PGHOST: Optional[str] = None
    PGPORT: int = 5432
    PGDATABASE: str = "databricks_postgres"   # base padrão do Lakebase (schema é PGSCHEMA)
    PGUSER: Optional[str] = None              # client_id do SP do app (Lakebase) ou user master (RDS)
    PGPASSWORD: Optional[str] = None          # senha estática (dev); senão gera credencial em runtime
    PGSSLMODE: str = "require"
    PGSCHEMA: str = "certifica"          # schema do produto (multi-tenant)

    # Caminho alternativo AWS RDS: token IAM de curta duração via boto3.
    RDS_IAM_AUTH: bool = False
    AWS_REGION: str = "us-east-1"

    # ── Geração de questões via LLM (Databricks Foundation Model API) ─────────
    # Qualquer chat model do workspace (ex.: databricks-claude-opus-4-8, gpt-oss-120b).
    LLM_ENDPOINT: str = "databricks-claude-opus-4-8"
    LLM_MAX_GENERATE: int = 10            # máx. de questões geradas por chamada

    # ── Autenticação (JWT + bcrypt) ───────────────────────────────────────────
    ENABLE_JWT_AUTH: bool = True
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRE_MINUTES: int = 720            # 12h
    ALLOW_SELF_REGISTER: bool = True         # trainees criam a própria conta no tenant
    PASS_MARK: int = 70                      # nota de corte padrão (override por tenant)
    # Operadores da plataforma (cross-tenant; veem /platform): "a@x.com,b@y.com"
    # Vazio por padrão — definido no setup do cliente (env SUPERADMIN_EMAILS).
    SUPERADMIN_EMAILS: str = ""
    # Tenant interno onde vivem os superadmins (login da consola /platform)
    PLATFORM_TENANT_SLUG: str = "platform"

    @property
    def superadmin_emails_list(self) -> List[str]:
        return [u.strip().lower() for u in self.SUPERADMIN_EMAILS.split(",") if u.strip()]

    # true = sem Databricks/RDS, usa seed_data.json local (dev)
    MOCK_MODE: bool = True

    # true = roda o seed (schema + banco global + tenants) no startup do app.
    # Idempotente; útil para demos onde não há como rodar o seed localmente.
    SEED_ON_STARTUP: bool = False

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
