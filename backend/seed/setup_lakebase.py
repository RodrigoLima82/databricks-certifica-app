"""
Cria (ou reusa) a instância **Lakebase Autoscaling** e popula os dados.

Faz o provisionamento ponta a ponta:
  1. cria o **projeto** Lakebase Autoscaling (se não existir) — branch `production` + endpoint primário;
  2. descobre o **host** e o **endpoint canônico** (projects/.../endpoints/...);
  3. (opcional) cria a **role** Postgres para o service principal do app;
  4. roda o **seed** (schema + tabelas + banco de questões) — via seed_lakebase.

Pré-requisitos:
  - `databricks auth login` (ou DATABRICKS_HOST/TOKEN no ambiente);
  - databricks-sdk >= 0.81 (`w.postgres`), psycopg, etc. (requirements do backend).

Uso:
    cd backend
    python -m seed.setup_lakebase                 # cria/reusa projeto + mostra config
    python -m seed.setup_lakebase --seed          # idem + roda o seed (schema/dados)
    python -m seed.setup_lakebase --seed \
        --project databricks-certifica --pg-version 16 \
        --app-sp <app-service-principal-client-id>   # cria a role do SP do app

⚠️  Criar um projeto provisiona recursos reais (faturáveis). É idempotente: se o
    projeto já existe, apenas reaproveita.
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("setup_lakebase")

DEFAULT_BRANCH = "production"


def _wait(op, what):
    """Espera uma long-running operation do w.postgres terminar."""
    log.info("aguardando %s…", what)
    if hasattr(op, "wait"):
        return op.wait()
    return op


def ensure_project(w, project_id: str, pg_version: str, budget_policy_id: str | None):
    """Cria o projeto Autoscaling se não existir; retorna o Project."""
    from databricks.sdk.service.postgres import Project, ProjectSpec

    name = f"projects/{project_id}"
    try:
        proj = w.postgres.get_project(name=name)
        log.info("projeto já existe: %s", name)
        return proj
    except Exception:
        log.info("criando projeto %s (pg %s)…", name, pg_version)

    spec = ProjectSpec(
        display_name=project_id,
        default_branch=DEFAULT_BRANCH,
        pg_version=pg_version,
        budget_policy_id=budget_policy_id,  # None p/ Autoscaling padrão
    )
    op = w.postgres.create_project(project=Project(spec=spec), project_id=project_id)
    proj = _wait(op, f"criação do projeto {name}")
    log.info("projeto criado: %s", name)
    return proj


def primary_endpoint(w, project_id: str):
    """Acha o endpoint primário (read-write) da branch production e seu host."""
    parent = f"projects/{project_id}/branches/{DEFAULT_BRANCH}"
    # o endpoint primário é criado junto com o projeto; pode levar alguns segundos
    for attempt in range(30):
        eps = list(w.postgres.list_endpoints(parent=parent))
        if eps:
            ep = eps[0]
            host = None
            st = getattr(ep, "status", None)
            hosts = getattr(st, "hosts", None) if st else None
            if hosts:
                host = getattr(hosts, "host", None)
            if host:
                return ep, host
        time.sleep(10)
    raise RuntimeError(f"endpoint primário não ficou pronto em {parent}")


def ensure_app_role(w, project_id: str, app_sp_client_id: str):
    """Cria a role Postgres para o service principal do app (idempotente)."""
    from databricks.sdk.service.postgres import Role
    parent = f"projects/{project_id}/branches/{DEFAULT_BRANCH}"
    try:
        existing = {r.name.split("/")[-1] for r in w.postgres.list_roles(parent=parent)}
        if app_sp_client_id in existing:
            log.info("role do app já existe: %s", app_sp_client_id)
            return
    except Exception:
        pass
    log.info("criando role do app (SP %s)…", app_sp_client_id)
    try:
        op = w.postgres.create_role(parent=parent, role=Role(), role_id=app_sp_client_id)
        _wait(op, "criação da role")
        log.info("role criada: %s", app_sp_client_id)
    except Exception as e:
        log.warning("não consegui criar a role automaticamente (%s). "
                    "Crie no console do Lakebase e dê GRANT no schema.", str(e)[:160])


def main():
    ap = argparse.ArgumentParser(description="Cria o Lakebase Autoscaling e popula os dados do Databricks Certifica.")
    ap.add_argument("--project", default=os.getenv("LAKEBASE_PROJECT_ID", "databricks-certifica"))
    ap.add_argument("--pg-version", default=os.getenv("LAKEBASE_PG_VERSION", "16"))
    ap.add_argument("--budget-policy-id", default=os.getenv("LAKEBASE_BUDGET_POLICY_ID"))
    ap.add_argument("--app-sp", default=os.getenv("APP_SP_CLIENT_ID"),
                    help="client_id do service principal do app (cria a role Postgres)")
    ap.add_argument("--schema", default=os.getenv("PGSCHEMA", "databricks_certifica"))
    ap.add_argument("--seed", action="store_true", help="rodar o seed (schema + tabelas + dados) ao final")
    args = ap.parse_args()

    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()

    ensure_project(w, args.project, args.pg_version, args.budget_policy_id)
    ep, host = primary_endpoint(w, args.project)
    endpoint_name = ep.name  # projects/<id>/branches/production/endpoints/<endpoint_id>
    log.info("endpoint pronto: %s", endpoint_name)
    log.info("host: %s", host)

    if args.app_sp:
        ensure_app_role(w, args.project, args.app_sp)

    # bloco de config p/ app.yaml / .env
    print("\n" + "=" * 70)
    print("Lakebase pronto. Use estes valores no app.yaml / backend/.env:")
    print("=" * 70)
    print(f"LAKEBASE_ENDPOINT={endpoint_name}")
    print(f"PGHOST={host}")
    print("PGPORT=5432")
    print("PGDATABASE=databricks_postgres")
    print(f"PGUSER={args.app_sp or '<email-ou-client_id-do-app>'}")
    print("PGSSLMODE=require")
    print(f"PGSCHEMA={args.schema}")
    print("=" * 70 + "\n")

    if args.seed:
        # garante que o seed conecte neste endpoint (set ANTES de importar a config)
        os.environ["MOCK_MODE"] = "false"
        os.environ["LAKEBASE_ENDPOINT"] = endpoint_name
        os.environ["PGHOST"] = host
        os.environ.setdefault("PGSCHEMA", args.schema)
        log.info("rodando o seed (schema + tabelas + dados)…")
        from seed.seed_lakebase import main as seed_main
        seed_main()
        log.info("seed concluído.")
    else:
        print("Para popular os dados agora: rode de novo com --seed "
              "(ou configure o .env e rode `python -m seed.seed_lakebase`).")


if __name__ == "__main__":
    main()
