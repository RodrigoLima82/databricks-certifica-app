# Databricks Certifica

Hub de preparação para **certificações Databricks** da Databricks — simulados
com correção e explicações, flashcards e geração de questões via IA (Claude Opus 4.8).

Inspirado no app *Databricks Get CertifAIed*, recriado com a arquitetura e identidade
visual Databricks: **FastAPI** (backend) + **React + TypeScript + Vite** (frontend), persistência
em **Lakebase (Postgres)** e deploy em **Databricks Apps** via Asset Bundles.

---

## Certificações cobertas

Banco com **608 questões** e **200 flashcards** (coletados do app de referência):

| Certificação | Questões | Flashcards |
|---|---|---|
| Data Engineer Associate | 100 | 40 |
| Data Engineer Professional | 100 | 40 |
| Data Analyst Associate | 110 | 40 |
| Machine Learning Associate | 100 | 40 |
| Machine Learning Professional | 98 | 40 |
| Generative AI Engineer Associate | 100 | 0 |

Cada questão tem: enunciado, opções, resposta(s) correta(s), explicação, tópico,
dificuldade (1–5) e tipo (`multiple_choice` / `multiple_select` / `true_false`).

---

## Estrutura

```
databricks-certifica-app/
├── Makefile
├── data/raw/                      ← banco coletado (1 JSON por certificação)
├── backend/
│   ├── requirements.txt
│   ├── app.yaml                   ← comando + env do Databricks App
│   ├── databricks.yml             ← Asset Bundle (targets dev/prod)
│   ├── seed/
│   │   ├── seed_data.json         ← banco consolidado (seed)
│   │   ├── setup_lakebase.py      ← cria o projeto Lakebase Autoscaling + popula (make setup-lakebase)
│   │   └── seed_lakebase.py       ← cria schema + popula o Lakebase (make seed)
│   └── app/
│       ├── main.py                ← FastAPI + SPA serve
│       ├── config.py              ← Settings (MOCK_MODE, Lakebase, LLM)
│       ├── db.py                  ← conexão Lakebase (OAuth) + fallback
│       ├── auth/workspace_client.py
│       ├── models/schemas.py
│       ├── services/
│       │   ├── store.py           ← seed em memória (mock)
│       │   ├── repo.py            ← repositório (Postgres | mock)
│       │   ├── test_service.py    ← montar + corrigir simulado
│       │   └── llm_gen.py         ← geração via Foundation Model API
│       └── api/{certifications,tests,generate}.py
└── frontend/
    └── src/
        ├── components/Layout.tsx
        ├── services/api.ts
        ├── types/index.ts
        └── pages/{Home,CertDetail,PracticeTest,Flashcards}.tsx
```

---

## Desenvolvimento local (mock, sem Databricks)

```bash
make install
make dev-backend      # terminal 1 — http://localhost:8005
make dev-frontend     # terminal 2 — http://localhost:3006
```

Com `MOCK_MODE=true` (padrão), o backend lê de `seed/seed_data.json`, e a flag
"Gerar via IA" produz questões sintéticas locais (sem chamar o LLM).

---

## Deploy no Databricks Free Edition

Todo o provisionamento (Lakebase Autoscaling + seed + Databricks App) é feito por um
único notebook — [`notebooks/setup_free_edition.py`](notebooks/setup_free_edition.py) —
executado **dentro do workspace**.

### 1. Buildar o frontend e commitar
O Databricks Apps serve os estáticos prontos (não roda `npm`), então o build precisa
estar no repositório:
```bash
make build            # gera backend/static/
git add -f backend/static && git commit -m "build frontend"
git push
```

### 2. Vincular o repositório no workspace
No Free Edition: **Workspace ▸ Repos ▸ Add repo** e aponte para este repositório Git.

### 3. Rodar o notebook de setup
Abra [`notebooks/setup_free_edition.py`](notebooks/setup_free_edition.py) no Git folder,
preencha os widgets (principalmente **`source_code_path`** — o caminho do `backend/`
dentro do Git folder, ex.: `/Workspace/Users/voce@exemplo.com/databricks-certifica-app/backend`)
e execute todas as células. O notebook, de forma idempotente:

1. cria o projeto **Lakebase Autoscaling** (branch `production` + endpoint primário);
2. cria o schema e popula o banco de questões (seed);
3. cria/atualiza o **Databricks App** com o Lakebase e o endpoint do Claude
   (`databricks-claude-opus-4-8`) anexados como *app resources* — a role Postgres do
   service principal e as permissões saem automaticamente;
4. gera o `app.yaml` (MOCK_MODE=false + Lakebase + LLM) e faz o **deploy**, imprimindo a URL.

> O `app.yaml` gerado contém o `JWT_SECRET` — não o committe em repositório público.

### Reexecução
Para atualizar só o código do app (após `git pull` no Git folder), rode o notebook com
`run_seed=false` e `deploy_app=true`.

---

## API

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/health` | Status + modo + endpoint LLM |
| GET | `/api/certifications/` | Lista certificações |
| GET | `/api/certifications/{id}` | Detalhe |
| GET | `/api/certifications/{id}/questions` | Banco de questões (filtro `topics`) |
| GET | `/api/certifications/{id}/flashcards` | Flashcards |
| POST | `/api/tests/` | Monta simulado (n questões, tópicos, flag IA) |
| POST | `/api/tests/submit` | Corrige e persiste a sessão no Lakebase |
| POST | `/api/generate/` | Gera questões novas via LLM |

Swagger: `/api/docs`.
