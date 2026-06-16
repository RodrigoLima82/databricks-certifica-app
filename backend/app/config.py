"""
Databricks Certifica — Configurações da aplicação.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Databricks Certifica"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

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

    # ── Lakebase Autoscaling (Postgres) ───────────────────────────────────────
    # Endpoint canônico: projects/{id}/branches/{branch}/endpoints/{endpoint}
    # Usado para gerar a credencial OAuth de curta duração (senha do Postgres).
    LAKEBASE_ENDPOINT: Optional[str] = None
    PGHOST: Optional[str] = None
    PGPORT: int = 5432
    PGDATABASE: str = "databricks_postgres"
    PGUSER: Optional[str] = None          # identidade Databricks (e-mail ou client_id do SP)
    PGPASSWORD: Optional[str] = None      # se setado, usa direto; senão gera via OAuth
    PGSSLMODE: str = "require"
    PGSCHEMA: str = "databricks_certifica"

    # ── Geração de questões via LLM (Foundation Model API) ────────────────────
    # Endpoint de serving do Claude Opus 4.8 no workspace (confirmar nome após login).
    LLM_ENDPOINT: str = "databricks-claude-opus-4-8"
    LLM_MAX_GENERATE: int = 10            # máx. de questões geradas por chamada

    # ── Autenticação (JWT + bcrypt) ───────────────────────────────────────────
    ENABLE_JWT_AUTH: bool = True
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRE_MINUTES: int = 720            # 12h
    ADMIN_EMAIL: str = ""                    # e-mail do admin (vê o painel)
    ALLOW_SELF_REGISTER: bool = True         # trainees criam a própria conta
    PASS_MARK: int = 70                      # nota de corte (%)
    # Usuários pré-provisionados (seed no startup): "a@x.com,b@y.com"
    PROVISIONED_USERS: str = ""
    # senha inicial dos usuários pré-provisionados — defina via env (não versionar segredo)
    PROVISIONED_INITIAL_PASSWORD: str = ""

    @property
    def provisioned_users_list(self) -> List[str]:
        return [u.strip().lower() for u in self.PROVISIONED_USERS.split(",") if u.strip()]

    @property
    def admin_email_norm(self) -> str:
        return self.ADMIN_EMAIL.strip().lower()

    # true = sem Databricks/Lakebase, usa seed_data.json local (dev)
    MOCK_MODE: bool = True

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
