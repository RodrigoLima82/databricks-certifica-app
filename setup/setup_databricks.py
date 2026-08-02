# Databricks notebook source
# MAGIC %md
# MAGIC # Certifica — Setup no Databricks (sem CLI)
# MAGIC
# MAGIC Este notebook provisiona **tudo** que o app Certifica precisa, direto de dentro do
# MAGIC workspace (não precisa de Databricks CLI na sua máquina):
# MAGIC
# MAGIC 1. **Lakebase** (Postgres) — cria a instância (ou reaproveita uma existente)
# MAGIC 2. **Secret scope** + `jwt_secret` (gerado aleatoriamente)
# MAGIC 3. **Databricks App** — cria o app e concede os recursos (secret + serving endpoint do LLM)
# MAGIC 4. **Permissão no Postgres** — dá ao service principal do app o papel de superusuário na instância
# MAGIC 5. **Deploy** do código (a build do frontend já vem versionada no repositório)
# MAGIC 6. **Seed** — no primeiro boot o app cria o schema, o banco de questões e o superadmin
# MAGIC
# MAGIC ### Pré-requisitos
# MAGIC - Este repositório clonado como **Git folder** no workspace (Repos), ou os arquivos em Workspace Files.
# MAGIC - Você é admin do workspace (ou tem permissão para criar Lakebase, Apps e secrets).
# MAGIC - Rode o notebook num cluster/serverless com internet (para instalar o `databricks-sdk` atualizado).
# MAGIC
# MAGIC > Preencha os widgets no topo e rode **Run all**.

# COMMAND ----------

# MAGIC %pip install --quiet "databricks-sdk>=0.81.0"
# MAGIC %restart_python

# COMMAND ----------

# DBTITLE 1,Parâmetros do setup (widgets)
dbutils.widgets.text("app_name", "certifica", "Nome do App")
dbutils.widgets.text("lakebase_instance", "certifica-db", "Instância Lakebase")
dbutils.widgets.text("lakebase_capacity", "CU_1", "Capacidade Lakebase (CU_1/CU_2/CU_4/CU_8)")
dbutils.widgets.text("pg_schema", "certifica", "Schema do Postgres")
dbutils.widgets.text("secret_scope", "certifica", "Secret scope")
dbutils.widgets.text("llm_endpoint", "auto", "LLM endpoint (auto = detectar)")
dbutils.widgets.text("superadmin_emails", "", "E-mail(s) do superadmin (separados por vírgula)")
dbutils.widgets.text("admin_password", "Certifica@2026", "Senha inicial do superadmin")
dbutils.widgets.text("default_tenant_slug", "", "Slug do 1º tenant (opcional)")
dbutils.widgets.text("default_tenant_name", "", "Nome do 1º tenant (opcional)")
dbutils.widgets.text("source_path", "../backend", "Caminho do código (backend) no workspace")

# COMMAND ----------

# DBTITLE 1,Coleta e valida os parâmetros
import os
import secrets as _secrets
import time
from pathlib import Path

APP_NAME          = dbutils.widgets.get("app_name").strip()
LAKEBASE_INSTANCE = dbutils.widgets.get("lakebase_instance").strip()
LAKEBASE_CAPACITY = dbutils.widgets.get("lakebase_capacity").strip() or "CU_1"
PG_SCHEMA         = dbutils.widgets.get("pg_schema").strip() or "certifica"
SECRET_SCOPE      = dbutils.widgets.get("secret_scope").strip() or "certifica"
LLM_ENDPOINT_IN   = dbutils.widgets.get("llm_endpoint").strip() or "auto"
SUPERADMIN_EMAILS = dbutils.widgets.get("superadmin_emails").strip()
ADMIN_PASSWORD    = dbutils.widgets.get("admin_password").strip() or "Certifica@2026"
DEFAULT_TENANT_SLUG = dbutils.widgets.get("default_tenant_slug").strip().lower()
DEFAULT_TENANT_NAME = dbutils.widgets.get("default_tenant_name").strip()
SOURCE_PATH_IN    = dbutils.widgets.get("source_path").strip()

assert APP_NAME, "Defina o nome do App."
assert LAKEBASE_INSTANCE, "Defina a instância Lakebase."
if not SUPERADMIN_EMAILS:
    raise ValueError("Defina ao menos um e-mail de superadmin — é quem administra a plataforma.")

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
me = w.current_user.me()
print(f"Workspace: {w.config.host}")
print(f"Usuário:   {me.user_name}")
print(f"App:       {APP_NAME}  |  Lakebase: {LAKEBASE_INSTANCE}  |  schema: {PG_SCHEMA}")

# COMMAND ----------

# DBTITLE 1,Resolve o caminho do código (backend) no workspace
# O deploy do App aponta para uma pasta do Workspace com app.yaml + app/ + static/.
# Tenta o caminho informado; se relativo, resolve contra a pasta deste notebook.
def _resolve_backend_path(raw: str) -> str:
    p = Path(raw)
    if p.is_absolute() and (p / "app.yaml").exists():
        return str(p)
    # relativo ao diretório de trabalho (pasta do notebook em Workspace Files)
    cand = (Path.cwd() / raw).resolve()
    if (cand / "app.yaml").exists():
        return str(cand)
    # fallback: deriva do path do notebook (…/setup/…) -> …/backend
    try:
        nb = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        repo_root = Path("/Workspace" + nb).parent.parent
        cand2 = repo_root / "backend"
        if (cand2 / "app.yaml").exists():
            return str(cand2)
    except Exception:
        pass
    raise FileNotFoundError(
        f"Não encontrei app.yaml a partir de '{raw}'. Ajuste o widget 'source_path' "
        f"para a pasta backend/ do repositório no workspace (cwd={Path.cwd()})."
    )

BACKEND_PATH = _resolve_backend_path(SOURCE_PATH_IN)
print(f"Código (backend): {BACKEND_PATH}")
assert (Path(BACKEND_PATH) / "static" / "index.html").exists(), \
    "backend/static/index.html não existe — a build do frontend deve estar versionada no repo."

# COMMAND ----------

# DBTITLE 1,1) Lakebase — cria (ou reaproveita) a instância Postgres
from databricks.sdk.service.database import DatabaseInstance

def ensure_lakebase(name: str, capacity: str) -> DatabaseInstance:
    try:
        inst = w.database.get_database_instance(name=name)
        print(f"Lakebase '{name}' já existe (state={inst.state}).")
    except Exception:
        print(f"Criando Lakebase '{name}' (capacity={capacity})… pode levar alguns minutos.")
        inst = w.database.create_database_instance_and_wait(
            DatabaseInstance(name=name, capacity=capacity)
        )
    # espera ficar disponível
    for _ in range(60):
        inst = w.database.get_database_instance(name=name)
        if str(inst.state) in ("DatabaseInstanceState.AVAILABLE", "AVAILABLE"):
            break
        time.sleep(10)
    print(f"Lakebase pronto: state={inst.state}  dns={inst.read_write_dns}")
    return inst

lakebase = ensure_lakebase(LAKEBASE_INSTANCE, LAKEBASE_CAPACITY)
PGHOST = lakebase.read_write_dns
assert PGHOST, "Lakebase sem read_write_dns — verifique o estado da instância."

# COMMAND ----------

# DBTITLE 1,2) Secret scope + jwt_secret
def ensure_scope(scope: str):
    scopes = [s.name for s in (w.secrets.list_scopes() or [])]
    if scope not in scopes:
        w.secrets.create_scope(scope=scope)
        print(f"Secret scope '{scope}' criado.")
    else:
        print(f"Secret scope '{scope}' já existe.")

ensure_scope(SECRET_SCOPE)

# jwt_secret: só cria se ainda não existir (não sobrescreve tokens já emitidos).
existing_keys = {s.key for s in (w.secrets.list_secrets(scope=SECRET_SCOPE) or [])}
if "jwt_secret" not in existing_keys:
    w.secrets.put_secret(scope=SECRET_SCOPE, key="jwt_secret", string_value=_secrets.token_urlsafe(48))
    print("jwt_secret gerado e gravado.")
else:
    print("jwt_secret já existe — mantido.")

# COMMAND ----------

# DBTITLE 1,3) LLM endpoint — auto-detecta o melhor disponível (ou usa o informado)
def pick_llm_endpoint(preference: str) -> str:
    names = [e.name for e in (w.serving_endpoints.list() or [])]
    if preference != "auto":
        if preference not in names:
            print(f"⚠️ '{preference}' não está na lista de endpoints; usando mesmo assim.")
        return preference
    # ordem de preferência (o app funciona com qualquer chat model)
    prefer = [
        "databricks-claude-opus-4-8", "databricks-claude-sonnet-4-5",
        "databricks-claude-3-7-sonnet", "databricks-gpt-oss-120b",
        "databricks-meta-llama-3-3-70b-instruct", "databricks-qwen35-122b-a10b",
    ]
    for p in prefer:
        if p in names:
            return p
    # senão, o primeiro chat model disponível
    chat = [e.name for e in w.serving_endpoints.list()
            if "gpt" in e.name or "llama" in e.name or "claude" in e.name or "qwen" in e.name]
    if chat:
        return chat[0]
    raise RuntimeError("Nenhum serving endpoint de chat encontrado no workspace.")

LLM_ENDPOINT = pick_llm_endpoint(LLM_ENDPOINT_IN)
print(f"LLM endpoint: {LLM_ENDPOINT}")

# COMMAND ----------

# DBTITLE 1,4) Cria o App (com recursos: secret + serving endpoint)
from databricks.sdk.service.apps import (
    App, AppResource, AppResourceSecret, AppResourceServingEndpoint,
    AppResourceSecretSecretPermission, AppResourceServingEndpointServingEndpointPermission,
)

app_resources = [
    AppResource(name="jwt-secret", secret=AppResourceSecret(
        scope=SECRET_SCOPE, key="jwt_secret",
        permission=AppResourceSecretSecretPermission.READ)),
    AppResource(name="llm-endpoint", serving_endpoint=AppResourceServingEndpoint(
        name=LLM_ENDPOINT,
        permission=AppResourceServingEndpointServingEndpointPermission.CAN_QUERY)),
]

try:
    app = w.apps.get(name=APP_NAME)
    print(f"App '{APP_NAME}' já existe — atualizando recursos.")
    app = w.apps.update(name=APP_NAME, app=App(
        name=APP_NAME, description="Certifica — multi-tenant Databricks certification prep",
        resources=app_resources))
except Exception:
    print(f"Criando App '{APP_NAME}'… (provisiona o compute, pode levar alguns minutos)")
    app = w.apps.create_and_wait(App(
        name=APP_NAME, description="Certifica — multi-tenant Databricks certification prep",
        resources=app_resources))

SP_CLIENT_ID = app.service_principal_client_id
APP_URL = app.url
print(f"App SP client_id: {SP_CLIENT_ID}")
print(f"App URL:          {APP_URL}")

# COMMAND ----------

# DBTITLE 1,5) Postgres — dá ao SP do app o papel de superusuário na instância
from databricks.sdk.service.database import (
    DatabaseInstanceRole, DatabaseInstanceRoleIdentityType, DatabaseInstanceRoleMembershipRole,
)

def ensure_pg_superuser(instance: str, sp_client_id: str):
    try:
        existing = w.database.get_database_instance_role(instance_name=instance, name=sp_client_id)
        print(f"Role PG do SP já existe: {existing.name}")
        return
    except Exception:
        pass
    w.database.create_database_instance_role(
        instance_name=instance,
        database_instance_role=DatabaseInstanceRole(
            name=sp_client_id,
            identity_type=DatabaseInstanceRoleIdentityType.SERVICE_PRINCIPAL,
            membership_role=DatabaseInstanceRoleMembershipRole.DATABRICKS_SUPERUSER,
        ),
    )
    print(f"SP {sp_client_id} agora é DATABRICKS_SUPERUSER na instância {instance}.")

ensure_pg_superuser(LAKEBASE_INSTANCE, SP_CLIENT_ID)

# COMMAND ----------

# DBTITLE 1,6) Gera o app.yaml (config resolvida deste cliente) e faz o deploy
# Origens permitidas (CORS): a URL do app + o domínio de Databricks Apps.
cors = f"{APP_URL},https://*.databricksapps.com" if APP_URL else "https://*.databricksapps.com"

app_yaml = f"""command:
  - sh
  - -c
  - uvicorn app.main:app --host 0.0.0.0 --port ${{DATABRICKS_APP_PORT:-8080}}

env:
  - name: MOCK_MODE
    value: "false"

  # ── Lakebase (Postgres) via OAuth do service principal do app ──────────────
  # Sem senha estática: o app gera credencial OAuth em runtime para a instância,
  # e o PGUSER é resolvido automaticamente para o client_id do SP.
  - name: LAKEBASE_INSTANCE_NAME
    value: "{LAKEBASE_INSTANCE}"
  - name: PGHOST
    value: "{PGHOST}"
  - name: PGPORT
    value: "5432"
  - name: PGDATABASE
    value: "databricks_postgres"
  - name: PGSSLMODE
    value: "require"
  - name: PGSCHEMA
    value: "{PG_SCHEMA}"

  # ── LLM (Foundation Model API) ─────────────────────────────────────────────
  - name: LLM_ENDPOINT
    value: "{LLM_ENDPOINT}"

  # ── Autenticação (JWT) ─────────────────────────────────────────────────────
  - name: ENABLE_JWT_AUTH
    value: "true"
  - name: JWT_SECRET
    valueFrom: jwt-secret
  - name: AUTH_HEADER
    value: "X-App-Auth"
  - name: SUPERADMIN_EMAILS
    value: "{SUPERADMIN_EMAILS}"
  - name: SEED_ADMIN_PASSWORD
    value: "{ADMIN_PASSWORD}"
  - name: PASS_MARK
    value: "70"

  # ── Primeiro tenant (opcional) ─────────────────────────────────────────────
  - name: DEFAULT_TENANT_SLUG
    value: "{DEFAULT_TENANT_SLUG}"
  - name: DEFAULT_TENANT_NAME
    value: "{DEFAULT_TENANT_NAME}"

  # ── Seed no primeiro boot (idempotente) ────────────────────────────────────
  - name: SEED_ON_STARTUP
    value: "true"

  - name: CORS_ORIGINS
    value: "{cors}"
"""

app_yaml_path = Path(BACKEND_PATH) / "app.yaml"
app_yaml_path.write_text(app_yaml, encoding="utf-8")
print(f"app.yaml gerado em {app_yaml_path}")
print(app_yaml)

# COMMAND ----------

# DBTITLE 1,Deploy do código
from databricks.sdk.service.apps import AppDeployment

print(f"Fazendo deploy de {BACKEND_PATH}…")
deployment = w.apps.deploy_and_wait(
    app_name=APP_NAME,
    app_deployment=AppDeployment(source_code_path=BACKEND_PATH),
)
print(f"Deploy: {deployment.status}")

# garante que o app está rodando
app = w.apps.get(name=APP_NAME)
if str(app.compute_status.state) not in ("ComputeState.ACTIVE", "ACTIVE"):
    print("Iniciando o compute do app…")
    w.apps.start_and_wait(name=APP_NAME)
    app = w.apps.get(name=APP_NAME)
print(f"App state: {app.compute_status.state if app.compute_status else '?'}")

# COMMAND ----------

# DBTITLE 1,7) Verificação
import urllib.request, json

health_url = f"{APP_URL}/api/health"
print(f"Checando {health_url} …")
try:
    token = w.config.oauth_token().access_token
    req = urllib.request.Request(health_url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Health:", json.loads(r.read().decode()))
except Exception as e:
    print(f"(Não consegui checar o health automaticamente: {e})")
    print("Abra a URL do app no navegador — o primeiro boot roda o seed e pode levar ~1 min.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Setup concluído
# MAGIC
# MAGIC Depois do primeiro boot (o app roda o **seed** automaticamente), acesse a URL do app:

# COMMAND ----------

print("=" * 70)
print(f"App URL:            {APP_URL}")
print(f"Console superadmin: {APP_URL}  → login no tenant 'platform'")
print(f"Superadmin:         {SUPERADMIN_EMAILS.split(',')[0].strip()}")
print(f"Senha inicial:      {ADMIN_PASSWORD}")
if DEFAULT_TENANT_SLUG:
    print(f"Primeiro tenant:    slug '{DEFAULT_TENANT_SLUG}' ({DEFAULT_TENANT_NAME or DEFAULT_TENANT_SLUG})")
print("=" * 70)
print("Dica: depois do 1º boot, você pode setar SEED_ON_STARTUP=false (opcional).")
print("      Novos clientes/tenants são criados pela própria console /platform.")
