# Certifica

**Multi-tenant** platform for **Databricks certification** prep — practice exams with
grading and explanations, flashcards, and AI-generated questions. Sellable to multiple
clients (tenants): each company gets its own branding, users and isolated results, while
sharing a common question bank.

**Deploy: Databricks Apps** (alternative AWS host documented below).
Available in **Spanish, Portuguese and English** (language selector in the UI).

- **Frontend** React + TypeScript + Vite → served by the backend (SPA under `/static`)
- **Backend** FastAPI (Python) → **Databricks Apps**
- **Data** Postgres → **Databricks Lakebase** (single schema, row-level multi-tenant)
- **LLM** question generation → **Databricks Foundation Model API** (any chat model)

---

## Multi-tenant model

**Row-level** isolation: the question bank (`certifications` / `questions` / `flashcards`)
is **global and shared**; everything client-specific carries a `tenant_id` (`users`,
`test_sessions`, `test_answers`). Branding (color, logo, name) is applied **at runtime**
per tenant, so a single build serves everyone.

```
   Browser  ──HTTPS──►  Databricks Apps
                        ┌─────────────────────────────────────────┐
                        │ FastAPI ──serves──► React SPA (/static)   │
                        │   ├── SQL ──► Lakebase (schema certifica) │  row-level per tenant_id
                        │   └── FMAPI ─► chat model                 │  question generation
                        └─────────────────────────────────────────┘
```

### Three access levels (admin areas)

| Role | Where | What it does |
|---|---|---|
| **Operator / superadmin** | Console **`/platform`** (login in the `platform` tenant) | Manages **clients (tenants)**: create, suspend/activate, "Open" link to each space. Manages **operators** (other console admin users: create / list / remove). |
| **Tenant admin** | Panel **`/admin`** (login in their tenant) | Manages **their company's users**: manual creation, edit name/area, change password, suspend/activate, delete. Sees tracking (attempts, scores) and exports PDF/CSV. |
| **End user (trainee)** | Tenant app (`/t/<slug>`) | Takes practice exams, flashcards, sees their history. Can self-register if the tenant allows it. |

> An **operator** is simply a user of the internal `platform` tenant. Anyone who logs into
> `platform` is a console superadmin. The `SUPERADMIN_EMAILS` env only seeds the first operator.

### How each role gets in
- **New client**: `/signup` (self-service, creates a tenant + its first admin) or an operator creates it from `/platform`.
- **A tenant's users**: go to `/` (Landing → type their company slug) or straight to `/t/<slug>` → branded login.
- **Operators**: `/platform`.

---

## Question bank (global, shared)

600+ questions and 200 flashcards (`backend/seed/seed_data.json`):

| Certification | Questions | Flashcards |
|---|---|---|
| Data Engineer Associate | 100 | 40 |
| Data Engineer Professional | 100 | 40 |
| Data Analyst Associate | 110 | 40 |
| Machine Learning Associate | 100 | 40 |
| Machine Learning Professional | 98 | 40 |
| Generative AI Engineer Associate | 100 | 0 |

---

## Local development (mock, no Databricks)

```bash
make install
make dev-backend      # terminal 1 — http://localhost:8005
make dev-frontend     # terminal 2 — http://localhost:3006
```

With `MOCK_MODE=true` (default) the backend reads from `seed/seed_data.json` and
"Generate with AI" produces local synthetic questions (no LLM call).

---

## Deploy on Databricks Apps

**See [SETUP.md](SETUP.md)** for the step by step. Two paths:

- **Setup notebook** (`setup/setup_databricks.py`) — recommended, **no CLI**: provisions
  Lakebase, secret, app, permissions and deploys from inside the workspace. The frontend
  build (`backend/static/`) is versioned, so no Node/npm is needed anywhere.
- **Databricks CLI** (Asset Bundle `backend/databricks.yml`) — for those who have the CLI.

The backend serves SPA and API on the same origin; the LLM uses the app's identity (FMAPI).
The app's JWT travels in a configurable header (`AUTH_HEADER`, default `X-App-Auth`) because
the Databricks Apps gateway consumes `Authorization` for its own OAuth. Postgres auth uses
the app's **service principal OAuth** (no static password).

---

## Deploy on AWS (alternative host)

`db.py` supports RDS (`PGPASSWORD` or IAM token) and the repo ships `backend/Dockerfile`
(App Runner), `amplify.yml` (frontend) and `make deploy-backend` (ECR). The frontend uses
`VITE_API_BASE_URL` to point at the backend when they live on different origins. See
`backend/.env.example` and `frontend/.env.example`.

---

## Structure

```
certifica/
├── SETUP.md                       ← install guide (notebook without CLI | CLI)
├── setup/setup_databricks.py      ← setup notebook (Lakebase + secret + app + deploy)
├── Makefile                       ← local dev + seed + deploy-prod (Databricks Apps)
├── amplify.yml                    ← frontend build spec (alternative AWS host)
├── backend/
│   ├── app.yaml                   ← Databricks App config (TEMPLATE: command + env + secrets)
│   ├── databricks.yml             ← Asset Bundle (prod target, generic)
│   ├── Dockerfile                 ← App Runner image (alternative AWS host)
│   ├── seed/seed_core.py          ← reusable DDL + load (app and notebook)
│   ├── seed/seed_db.py            ← seed via app.db (startup / make seed)
│   └── app/
│       ├── main.py                ← FastAPI + serves SPA from /static
│       ├── config.py              ← Settings (MOCK_MODE, Lakebase/RDS, LLM, JWT, superadmins)
│       ├── db.py                  ← Postgres: Lakebase OAuth | RDS (IAM) | static password
│       ├── auth/                  ← JWT (tenant_id + roles) + bcrypt + WorkspaceClient (FMAPI)
│       ├── services/              ← tenants, users, repo, test_service, llm_gen, pdf_report
│       └── api/                   ← tenants(+platform), certifications, tests, generate, auth, tracking
└── frontend/
    └── src/
        ├── i18n/                  ← es / pt / en + language selector
        ├── context/               ← Auth + Theme (runtime branding) + i18n
        └── pages/                 ← Landing, Login, Signup, Home, CertDetail, PracticeTest,
                                      Flashcards, History, Admin, AdminUser, Platform
```

---

## Status

- Row-level multi-tenant with runtime branding + i18n (es/pt/en).
- `/platform` console: tenant + operator management.
- `/admin` panel: full tenant user management + tracking + PDF/CSV export.
- Configurable LLM (any workspace chat model). Translated UI and PDF report.

> **White-label**: the product is not specific to any client. Brand, superadmin and first
> tenant are configured at setup time (nothing hardcoded). See [SETUP.md](SETUP.md).
