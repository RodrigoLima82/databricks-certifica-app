"""
Cria o schema multi-tenant e popula o Postgres (Lakebase / RDS).

- Banco de questões (certifications/questions/flashcards) é GLOBAL (compartilhado).
- users/test_sessions/test_answers são escopados por tenant_id.
- Cria o tenant interno 'platform' (consola superadmin) e, opcionalmente, um
  primeiro tenant (cliente) se DEFAULT_TENANT_SLUG estiver definido.
- Cria o(s) usuário(s) superadmin (SUPERADMIN_EMAILS) com senha SEED_ADMIN_PASSWORD.

A lógica (DDL + carga) vive em seed_core.py e é compartilhada com o notebook de
setup. Aqui só resolvemos a conexão via app.db.get_conn() e as configs via env.

Uso:  cd backend && python -m seed.seed_db
Idempotente: CREATE ... IF NOT EXISTS e ON CONFLICT DO NOTHING.
"""
import logging
import os
import sys
from pathlib import Path

# permite rodar como `python -m seed.seed_db` a partir de backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.db import get_conn  # noqa: E402
from seed.seed_core import seed_with_connection  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("seed")

ADMIN_PW = os.environ.get("SEED_ADMIN_PASSWORD", "Certifica@2026")


def run_seed() -> dict:
    """Cria schema/tabelas e popula o Postgres. Idempotente.

    Reutilizável a partir do CLI (`python -m seed.seed_db`) ou do startup do
    app (SEED_ON_STARTUP=true).
    """
    s = get_settings()
    with get_conn() as conn:   # autocommit=True
        return seed_with_connection(
            conn,
            schema=s.PGSCHEMA,
            platform_slug=s.PLATFORM_TENANT_SLUG,
            superadmin_emails=s.superadmin_emails_list,
            admin_password=ADMIN_PW,
            default_tenant_slug=s.DEFAULT_TENANT_SLUG,
            default_tenant_name=s.DEFAULT_TENANT_NAME,
            default_tenant_color=s.DEFAULT_TENANT_COLOR,
            default_tenant_logo=s.DEFAULT_TENANT_LOGO,
            log=log.info,
        )


def main():
    if get_settings().MOCK_MODE:
        log.error("MOCK_MODE=true — configure o .env para o Postgres antes de semear.")
        sys.exit(1)
    run_seed()
    log.info("Seed multi-tenant concluído.")


if __name__ == "__main__":
    main()
