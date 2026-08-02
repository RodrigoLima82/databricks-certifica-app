# Setup do Certifica no Databricks

Guia para provisionar o Certifica num workspace Databricks. Há **dois caminhos** —
escolha o primeiro se você **não tem o Databricks CLI** na máquina.

---

## Caminho A — Notebook de setup (recomendado, sem CLI)

Provisiona tudo de dentro do workspace: Lakebase, secret, app, permissões e deploy.

### 1. Traga o código para o workspace
No Databricks: **Workspace → Repos → Add Repo** e clone este repositório
(`https://github.com/mousastech/certifica.git`).

> A build do frontend (`backend/static/`) já vem **versionada** no repo, então não é
> preciso rodar `npm`/Node em lugar nenhum.

### 2. Abra e rode o notebook
Abra **`setup/setup_databricks.py`**. Preencha os widgets no topo:

| Widget | O que é | Exemplo |
|---|---|---|
| `app_name` | Nome do Databricks App | `certifica` |
| `lakebase_instance` | Nome da instância Lakebase (criada se não existir) | `certifica-db` |
| `lakebase_capacity` | Capacidade da instância | `CU_1` |
| `pg_schema` | Schema do Postgres | `certifica` |
| `secret_scope` | Secret scope (criado se não existir) | `certifica` |
| `llm_endpoint` | Endpoint do LLM (`auto` detecta o melhor disponível) | `auto` |
| `superadmin_emails` | E-mail(s) do superadmin (vírgula separa vários) | `voce@empresa.com` |
| `admin_password` | Senha inicial do superadmin | `Certifica@2026` |
| `default_tenant_slug` | (Opcional) 1º tenant/cliente já criado | `minhaempresa` |
| `default_tenant_name` | (Opcional) Nome do 1º tenant | `Minha Empresa` |
| `source_path` | Caminho do `backend/` no workspace | `../backend` |

Depois: **Run all**. O notebook:
1. cria/reaproveita a **Lakebase**;
2. cria o **secret scope** + `jwt_secret`;
3. escolhe o **LLM endpoint** (auto-detecção com override);
4. cria o **App** e concede os recursos (secret + serving endpoint);
5. dá ao **service principal** do app o papel de superusuário no Postgres;
6. gera o `app.yaml` e faz o **deploy**;
7. no 1º boot o app roda o **seed** (schema + banco de questões + superadmin).

### 3. Acesse
Abra a **URL do app** (impressa no fim do notebook). Faça login no tenant `platform`
com o e-mail/senha do superadmin. A partir da console `/platform` você cria os
clientes (tenants) — cada um com seu próprio branding e usuários.

---

## Caminho B — Databricks CLI (Asset Bundle)

Para quem tem a [CLI](https://docs.databricks.com/dev-tools/cli/) configurada.

```bash
# 1. Autentique num profile
databricks auth login --host https://<workspace>.cloud.databricks.com --profile meucliente

# 2. Crie o secret scope + jwt_secret
databricks secrets create-scope certifica -p meucliente
databricks secrets put-secret certifica jwt_secret --string-value "$(openssl rand -base64 48)" -p meucliente

# 3. Crie a Lakebase (uma vez) — via UI (Compute → Lakebase) ou CLI
#    e anote o read_write_dns (PGHOST).

# 4. Edite backend/app.yaml: PGHOST, LLM_ENDPOINT, SUPERADMIN_EMAILS, CORS_ORIGINS.
#    Edite backend/databricks.yml: host + profile do target 'prod'.

# 5. Deploy
cd backend
databricks bundle deploy -t prod -p meucliente
databricks bundle run certifica -t prod -p meucliente
```

Depois do deploy, dê ao **service principal do app** acesso ao Postgres
(role `DATABRICKS_SUPERUSER` na instância Lakebase) — via UI da instância ou
repetindo o passo 5 do notebook.

---

## O que é criado

| Recurso | Papel |
|---|---|
| **Databricks App** | Serve o FastAPI + SPA React (`/static`) |
| **Lakebase (Postgres)** | Um schema multi-tenant (`certifica`) — banco de questões global + dados por tenant |
| **Secret scope** | `jwt_secret` (assinatura dos tokens do app) |
| **Serving endpoint** | LLM para gerar questões/explicações (Foundation Model API) |
| **Tenant `platform`** | Console do superadmin (gerencia clientes) |

## Variáveis de ambiente (app.yaml)

As principais (todas com defaults neutros — nada de marca hardcoded):

- `LAKEBASE_INSTANCE_NAME`, `PGHOST`, `PGSCHEMA` — conexão ao Postgres (auth por OAuth do SP).
- `LLM_ENDPOINT` — qualquer chat model do workspace.
- `SUPERADMIN_EMAILS` — quem administra a plataforma (console `/platform`).
- `SEED_ADMIN_PASSWORD` — senha inicial do(s) superadmin(s).
- `DEFAULT_TENANT_SLUG` / `DEFAULT_TENANT_NAME` — (opcional) 1º cliente criado no seed.
- `AUTH_HEADER` — header do JWT do app (default `X-App-Auth`).
- `SEED_ON_STARTUP` — `true` no 1º boot; pode virar `false` depois.
