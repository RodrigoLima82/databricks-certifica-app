# Databricks notebook source
# MAGIC %md
# MAGIC # Databricks Certifica — Setup no Databricks Free Edition
# MAGIC
# MAGIC Provisiona **tudo** de ponta a ponta dentro de um workspace **Free Edition**:
# MAGIC
# MAGIC 1. **Lakebase Autoscaling** — cria o projeto + branch `production` + endpoint primário (idempotente).
# MAGIC 2. **Schema + seed** — cria as tabelas e popula o banco de questões (`seed/seed_data.json`).
# MAGIC 3. **Databricks App** — cria/atualiza o app apontando para este Git folder, com o
# MAGIC    Lakebase e o endpoint do Claude anexados como *app resources* (a role Postgres do
# MAGIC    service principal e as permissões são concedidas automaticamente).
# MAGIC 4. **app.yaml** — grava a config do app (MOCK_MODE=false + Lakebase + LLM) no Git folder.
# MAGIC 5. **Deploy** — sobe o app e imprime a URL.
# MAGIC
# MAGIC > **Pré-requisitos**
# MAGIC > - Este notebook deve rodar **dentro do Git folder** do projeto (Workspace ▸ Repos ▸ Add repo).
# MAGIC > - O frontend já precisa estar **buildado e commitado** em `backend/static/`
# MAGIC >   (rode `make build` localmente e faça commit) — o Databricks Apps não roda `npm`.
# MAGIC > - Lakebase Autoscaling disponível no workspace (confirmado no Free Edition).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Dependências (pg8000 para o seed)
# MAGIC
# MAGIC Usamos **`pg8000`** — driver Postgres **100% Python**, sem `libpq`/extensão C.
# MAGIC Drivers com C nativo (`psycopg`/`psycopg2`) dão **SIGABRT no import** no runtime
# MAGIC serverless ML do Databricks (conflito de OpenSSL/libpq). O pg8000 funciona em
# MAGIC qualquer runtime.

# COMMAND ----------

# MAGIC %pip install -q "pg8000>=1.30" "databricks-sdk>=0.81.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Parâmetros
# MAGIC
# MAGIC `source_code_path` é o caminho do **backend** dentro do Git folder (onde fica o `app.yaml`).
# MAGIC Ex.: `/Workspace/Users/voce@exemplo.com/databricks-certifica-app/backend`.

# COMMAND ----------

dbutils.widgets.text("project_id",        "databricks-certifica",          "Lakebase project id")
dbutils.widgets.text("pg_version",        "16",                            "Postgres version")
dbutils.widgets.text("schema",            "databricks_certifica",          "Schema Postgres")
dbutils.widgets.text("app_name",          "databricks-certifica",          "Databricks App name")
dbutils.widgets.text("source_code_path",  "",                              "Caminho do backend (vazio = auto-detecta)")
dbutils.widgets.text("llm_endpoint",      "databricks-claude-opus-4-8",    "Serving endpoint (LLM)")
dbutils.widgets.text("admin_email",       "",                              "E-mail do admin do app")
dbutils.widgets.dropdown("run_seed",      "true", ["true", "false"],       "Rodar o seed (dados)?")
dbutils.widgets.dropdown("deploy_app",    "true", ["true", "false"],       "Criar/atualizar e deployar o app?")

PROJECT_ID  = dbutils.widgets.get("project_id").strip()
PG_VERSION  = dbutils.widgets.get("pg_version").strip()
SCHEMA      = dbutils.widgets.get("schema").strip()
APP_NAME    = dbutils.widgets.get("app_name").strip()
SRC_PATH    = dbutils.widgets.get("source_code_path").strip().rstrip("/")
LLM_ENDPOINT = dbutils.widgets.get("llm_endpoint").strip()
ADMIN_EMAIL = dbutils.widgets.get("admin_email").strip()
RUN_SEED    = dbutils.widgets.get("run_seed") == "true"
DEPLOY_APP  = dbutils.widgets.get("deploy_app") == "true"
BRANCH      = "production"
PGDATABASE  = "databricks_postgres"

import logging, time, json, secrets, textwrap
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("setup-fe")

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
ME = w.current_user.me().user_name
if not ADMIN_EMAIL:
    ADMIN_EMAIL = ME
log.info("workspace: %s | usuário: %s", w.config.host, ME)

# auto-detecta o caminho do backend a partir da localização deste notebook
# (este notebook fica em <repo>/notebooks/...; o backend fica em <repo>/backend)
if not SRC_PATH:
    nb = (dbutils.notebook.entry_point.getDbutils().notebook()
          .getContext().notebookPath().get())          # ex.: /Users/<me>/databricks-certifica-app/notebooks/setup_free_edition
    repo_root = nb.rsplit("/notebooks/", 1)[0]
    SRC_PATH = f"/Workspace{repo_root}/backend"
    log.info("source_code_path auto-detectado: %s", SRC_PATH)
assert SRC_PATH, "Não consegui detectar o caminho — preencha o widget 'source_code_path' (caminho do backend no Git folder)."

# COMMAND ----------

# MAGIC %md ## 2. Lakebase Autoscaling — projeto + endpoint primário (idempotente)

# COMMAND ----------

from databricks.sdk.service.postgres import Project, ProjectSpec

def _wait(op, what):
    log.info("aguardando %s…", what)
    return op.wait() if hasattr(op, "wait") else op

def ensure_project(project_id: str):
    name = f"projects/{project_id}"
    # IMPORTANTE: get_project NÃO lança erro quando o projeto não existe (retorna um
    # stub vazio) — a checagem de existência tem que ser via list_projects().
    if name in {p.name for p in w.postgres.list_projects()}:
        log.info("projeto já existe (ativo): %s", name)
        return
    # pode existir em estado soft-deleted (id fica reservado até o purge) — nesse caso
    # create falha com "already exists"; o correto é restaurar com undelete_project.
    try:
        p = w.postgres.get_project(name=name)
        if getattr(p, "delete_time", None):
            log.info("projeto em estado soft-deleted; restaurando…")
            _wait(w.postgres.undelete_project(name=name), "undelete do projeto")
            return
    except Exception:
        pass
    # criar do zero — default_branch exige o formato canônico projects/{id}/branches/{branch}
    log.info("criando projeto %s (pg %s)…", name, PG_VERSION)
    spec = ProjectSpec(display_name=project_id,
                       default_branch=f"projects/{project_id}/branches/{BRANCH}",
                       pg_version=PG_VERSION)
    _wait(w.postgres.create_project(project=Project(spec=spec), project_id=project_id),
          f"criação de {name}")
    log.info("projeto criado: %s", name)

def primary_endpoint(project_id: str):
    parent = f"projects/{project_id}/branches/{BRANCH}"
    for _ in range(40):
        eps = list(w.postgres.list_endpoints(parent=parent))
        if eps:
            ep = eps[0]
            st = getattr(ep, "status", None)
            hosts = getattr(st, "hosts", None) if st else None
            host = getattr(hosts, "host", None) if hosts else None
            if host:
                return ep.name, host
        time.sleep(10)
    raise RuntimeError(f"endpoint primário não ficou pronto em {parent}")

ensure_project(PROJECT_ID)
ENDPOINT_NAME, PGHOST = primary_endpoint(PROJECT_ID)
log.info("LAKEBASE_ENDPOINT = %s", ENDPOINT_NAME)
log.info("PGHOST            = %s", PGHOST)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Schema + seed
# MAGIC
# MAGIC Conecta como **o usuário atual** (credencial OAuth de curta duração gerada para o endpoint)
# MAGIC e cria o schema/tabelas + popula o banco de questões. Idempotente.

# COMMAND ----------

DDL = """
CREATE SCHEMA IF NOT EXISTS {s};
CREATE TABLE IF NOT EXISTS {s}.certifications (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT, level TEXT,
    description TEXT, exam_guide_url TEXT, topics JSONB, resources JSONB);
CREATE TABLE IF NOT EXISTS {s}.questions (
    id TEXT PRIMARY KEY, certification_id TEXT NOT NULL REFERENCES {s}.certifications(id),
    topic TEXT, question_text TEXT NOT NULL, question_type TEXT NOT NULL DEFAULT 'multiple_choice',
    options JSONB NOT NULL, correct_answers JSONB NOT NULL, explanation TEXT,
    difficulty INT DEFAULT 3, is_ai_generated BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_questions_cert ON {s}.questions(certification_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic ON {s}.questions(certification_id, topic);
CREATE TABLE IF NOT EXISTS {s}.flashcards (
    id TEXT PRIMARY KEY, certification_id TEXT NOT NULL REFERENCES {s}.certifications(id),
    topic TEXT, front TEXT NOT NULL, back TEXT NOT NULL, difficulty INT DEFAULT 2);
CREATE INDEX IF NOT EXISTS idx_flashcards_cert ON {s}.flashcards(certification_id);
CREATE TABLE IF NOT EXISTS {s}.users (
    email TEXT PRIMARY KEY, name TEXT NOT NULL, password_hash TEXT NOT NULL,
    must_change_password BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS {s}.test_sessions (
    id TEXT PRIMARY KEY, certification_id TEXT, user_email TEXT, num_questions INT,
    topics JSONB, ai_generated BOOLEAN DEFAULT FALSE, score_pct REAL, correct INT, total INT,
    passed BOOLEAN DEFAULT FALSE, repeated_questions INT DEFAULT 0, duration_sec REAL,
    created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_sessions_user ON {s}.test_sessions(user_email, created_at);
CREATE TABLE IF NOT EXISTS {s}.test_answers (
    id TEXT PRIMARY KEY, session_id TEXT REFERENCES {s}.test_sessions(id), question_id TEXT,
    topic TEXT, selected JSONB, is_correct BOOLEAN);
CREATE INDEX IF NOT EXISTS idx_answers_session ON {s}.test_answers(session_id);
"""

def connect(user: str):
    import pg8000.dbapi, ssl
    cred = w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = pg8000.dbapi.connect(
        host=PGHOST, port=5432, database=PGDATABASE, user=user, password=cred.token,
        ssl_context=ctx, timeout=30)
    conn.autocommit = True
    return conn

def run_script(cur, script: str):
    """pg8000 executa 1 statement por vez — quebra o script por ';'."""
    for stmt in script.split(";"):
        if stmt.strip():
            cur.execute(stmt)

if RUN_SEED:
    seed_file = f"{SRC_PATH}/seed/seed_data.json"
    data = json.loads(open(seed_file, encoding="utf-8").read())
    certs, questions, flashcards = data["certifications"], data["questions"], data["flashcards"]
    conn = connect(ME)
    cur = conn.cursor()
    try:
        log.info("criando schema/tabelas em '%s'…", SCHEMA)
        run_script(cur, DDL.format(s=SCHEMA))
        for c in certs:
            cur.execute(
                f"INSERT INTO {SCHEMA}.certifications "
                "(id,name,type,level,description,exam_guide_url,topics,resources) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET "
                "name=EXCLUDED.name, exam_guide_url=EXCLUDED.exam_guide_url, "
                "topics=EXCLUDED.topics, resources=EXCLUDED.resources",
                (c["id"], c["name"], c.get("type"), c.get("level"), c.get("description"),
                 c.get("exam_guide_url"), json.dumps(c.get("topics", [])),
                 json.dumps(c.get("resources", []))))
        log.info("  %d certificações", len(certs))
        for q in questions:
            cur.execute(
                f"INSERT INTO {SCHEMA}.questions "
                "(id,certification_id,topic,question_text,question_type,options,"
                "correct_answers,explanation,difficulty,is_ai_generated) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (q["id"], q["certification_id"], q.get("topic"), q["question_text"],
                 q.get("question_type", "multiple_choice"), json.dumps(q["options"]),
                 json.dumps(q["correct_answers"]), q.get("explanation", ""),
                 q.get("difficulty", 3), q.get("is_ai_generated", False)))
        log.info("  %d questões", len(questions))
        for f in flashcards:
            cur.execute(
                f"INSERT INTO {SCHEMA}.flashcards (id,certification_id,topic,front,back,difficulty) "
                "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (f["id"], f["certification_id"], f.get("topic"), f["front"], f["back"],
                 f.get("difficulty", 2)))
        log.info("  %d flashcards", len(flashcards))
    finally:
        cur.close()
        conn.close()
    log.info("seed concluído.")
else:
    log.info("seed pulado (run_seed=false).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Databricks App — criar/atualizar com Lakebase + LLM como *app resources*
# MAGIC
# MAGIC O resource **Postgres** (`CAN_CONNECT_AND_CREATE`) faz o Databricks criar a role do
# MAGIC service principal do app e conceder acesso ao banco automaticamente. O resource
# MAGIC **serving endpoint** (`CAN_QUERY`) libera o app para chamar o Claude.

# COMMAND ----------

from databricks.sdk.service.apps import (
    App, AppResource, AppResourcePostgres, AppResourcePostgresPostgresPermission,
    AppResourceServingEndpoint, AppResourceServingEndpointServingEndpointPermission,
)

SP_CLIENT_ID = None
if DEPLOY_APP:
    parent = f"projects/{PROJECT_ID}/branches/{BRANCH}"
    # o id do database no resource é o NOME CANÔNICO (ex.: .../databases/databricks-postgres,
    # com hífen) — diferente do nome de conexão Postgres (databricks_postgres). Descobrir:
    DB_RESOURCE = list(w.postgres.list_databases(parent=parent))[0].name
    log.info("database (resource) = %s", DB_RESOURCE)
    resources = [
        AppResource(
            name="lakebase",
            postgres=AppResourcePostgres(
                branch=parent,
                database=DB_RESOURCE,
                permission=AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE)),
        AppResource(
            name="llm",
            serving_endpoint=AppResourceServingEndpoint(
                name=LLM_ENDPOINT,
                permission=AppResourceServingEndpointServingEndpointPermission.CAN_QUERY)),
    ]
    try:
        app = w.apps.get(name=APP_NAME)
        log.info("app já existe: %s — atualizando recursos…", APP_NAME)
        app.resources = resources
        app.default_source_code_path = SRC_PATH
        app = w.apps.update(name=APP_NAME, app=app)
    except Exception:
        log.info("criando app %s…", APP_NAME)
        app = w.apps.create_and_wait(app=App(
            name=APP_NAME,
            description="Databricks Certifica — simulados de certificações Databricks",
            default_source_code_path=SRC_PATH,
            resources=resources))
    SP_CLIENT_ID = app.service_principal_client_id
    log.info("service principal (client_id) do app = %s", SP_CLIENT_ID)
else:
    log.info("deploy do app pulado (deploy_app=false).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. GRANTs no schema para o service principal do app
# MAGIC
# MAGIC O resource concede acesso ao banco; aqui garantimos acesso ao **nosso schema**
# MAGIC (`databricks_certifica`), que foi criado pelo usuário do notebook.

# COMMAND ----------

if DEPLOY_APP and SP_CLIENT_ID:
    role = SP_CLIENT_ID  # a role Postgres do SP = client_id
    grants = f'''
    GRANT USAGE ON SCHEMA {SCHEMA} TO "{role}";
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {SCHEMA} TO "{role}";
    ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA}
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{role}";
    '''
    try:
        conn = connect(ME)
        cur = conn.cursor()
        try:
            run_script(cur, grants)
        finally:
            cur.close()
            conn.close()
        log.info("GRANTs aplicados ao SP %s no schema %s", role, SCHEMA)
    except Exception as e:
        log.warning("não consegui aplicar os GRANTs automaticamente: %s", str(e)[:300])
        log.warning("rode manualmente (como dono do schema):\n%s", textwrap.dedent(grants))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Gerar `app.yaml` no Git folder
# MAGIC
# MAGIC Escreve a config do app para o **Free Edition** (Lakebase real + LLM).
# MAGIC O `JWT_SECRET` é gerado aqui — **não committe este `app.yaml`** num repo público.

# COMMAND ----------

if DEPLOY_APP:
    jwt_secret = secrets.token_hex(32)
    app_yaml = f"""command:
  - sh
  - -c
  - uvicorn app.main:app --host 0.0.0.0 --port ${{DATABRICKS_APP_PORT:-8080}}

env:
  - name: MOCK_MODE
    value: "false"

  # ── Lakebase Autoscaling (Postgres) ──────────────────────────────────────
  - name: LAKEBASE_ENDPOINT
    value: "{ENDPOINT_NAME}"
  - name: PGHOST
    value: "{PGHOST}"
  - name: PGPORT
    value: "5432"
  - name: PGDATABASE
    value: "{PGDATABASE}"
  - name: PGUSER
    value: "{SP_CLIENT_ID}"
  - name: PGSSLMODE
    value: "require"
  - name: PGSCHEMA
    value: "{SCHEMA}"

  # ── LLM (Foundation Model API) ───────────────────────────────────────────
  - name: LLM_ENDPOINT
    value: "{LLM_ENDPOINT}"

  # ── Autenticação (JWT) ───────────────────────────────────────────────────
  - name: ENABLE_JWT_AUTH
    value: "true"
  - name: JWT_SECRET
    value: "{jwt_secret}"
  - name: ADMIN_EMAIL
    value: "{ADMIN_EMAIL}"
  - name: ALLOW_SELF_REGISTER
    value: "true"
  - name: PASS_MARK
    value: "70"

  - name: CORS_ORIGINS
    value: "https://*.databricksapps.com,https://*.cloud.databricks.com"
"""
    import io
    from databricks.sdk.service.workspace import ImportFormat
    out = f"{SRC_PATH}/app.yaml"
    w.workspace.upload(out, io.BytesIO(app_yaml.encode()),
                       format=ImportFormat.AUTO, overwrite=True)
    log.info("app.yaml gravado em %s", out)
    print(app_yaml)

# COMMAND ----------

# MAGIC %md ## 7. Deploy do app

# COMMAND ----------

if DEPLOY_APP:
    from databricks.sdk.service.apps import AppDeployment
    log.info("deployando %s a partir de %s…", APP_NAME, SRC_PATH)
    dep = w.apps.deploy_and_wait(
        app_name=APP_NAME,
        app_deployment=AppDeployment(source_code_path=SRC_PATH))
    app = w.apps.get(name=APP_NAME)
    print("\n" + "=" * 70)
    print("App no ar! 🎉")
    print("URL:        ", app.url)
    print("Status:     ", getattr(getattr(app, "app_status", None), "state", None))
    print("Deployment: ", getattr(getattr(dep, "status", None), "state", None))
    print("=" * 70)
else:
    log.info("deploy pulado. Para subir o app, rode com deploy_app=true.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pronto ✅
# MAGIC
# MAGIC - **Lakebase Autoscaling** provisionado e populado.
# MAGIC - **App** criado, com Lakebase + Claude anexados, e no ar.
# MAGIC
# MAGIC ### Reexecução
# MAGIC O notebook é idempotente — pode rodar de novo após dar `git pull` no Git folder
# MAGIC (ex.: depois de rebuildar o frontend). Para só atualizar o código do app, mantenha
# MAGIC `run_seed=false` e `deploy_app=true`.
# MAGIC
# MAGIC ### Lembretes
# MAGIC - `backend/static/` precisa estar buildado e commitado (`make build`).
# MAGIC - O `app.yaml` gerado contém o `JWT_SECRET` — não committe num repo público.
