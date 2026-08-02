"""
Núcleo reutilizável do seed (DDL + carga de dados), agnóstico de como a conexão
é obtida. Usado por:
  - seed_db.run_seed() ............ conexão via app.db.get_conn() (startup do app)
  - notebook de setup ............. conexão psycopg direta (credencial do workspace)

Idempotente: CREATE ... IF NOT EXISTS + ON CONFLICT. Não depende de pydantic/app,
então pode ser importado num notebook Databricks sem instalar o backend inteiro.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable, Optional

SEED_JSON = Path(__file__).resolve().parent / "seed_data.json"

DDL = """
CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.tenants (
    id                  TEXT PRIMARY KEY,
    slug                TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    primary_color       TEXT DEFAULT '#2272B4',
    logo_url            TEXT,
    pass_mark           INT DEFAULT 70,
    allow_self_register BOOLEAN DEFAULT TRUE,
    status              TEXT DEFAULT 'active',
    program             JSONB,
    routes              JSONB,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.tenant_domains (
    email_domain TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL REFERENCES {schema}.tenants(id)
);

CREATE TABLE IF NOT EXISTS {schema}.certifications (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT, level TEXT,
    description TEXT, exam_guide_url TEXT, topics JSONB, resources JSONB
);

CREATE TABLE IF NOT EXISTS {schema}.questions (
    id TEXT PRIMARY KEY,
    certification_id TEXT NOT NULL REFERENCES {schema}.certifications(id),
    topic TEXT, question_text TEXT NOT NULL,
    question_type TEXT NOT NULL DEFAULT 'multiple_choice',
    options JSONB NOT NULL, correct_answers JSONB NOT NULL,
    explanation TEXT, difficulty INT DEFAULT 3,
    is_ai_generated BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_questions_cert ON {schema}.questions(certification_id);

CREATE TABLE IF NOT EXISTS {schema}.flashcards (
    id TEXT PRIMARY KEY,
    certification_id TEXT NOT NULL REFERENCES {schema}.certifications(id),
    topic TEXT, front TEXT NOT NULL, back TEXT NOT NULL, difficulty INT DEFAULT 2
);
CREATE INDEX IF NOT EXISTS idx_flashcards_cert ON {schema}.flashcards(certification_id);

CREATE TABLE IF NOT EXISTS {schema}.users (
    tenant_id            TEXT NOT NULL REFERENCES {schema}.tenants(id),
    email                TEXT NOT NULL,
    name                 TEXT NOT NULL,
    password_hash        TEXT NOT NULL,
    is_admin             BOOLEAN DEFAULT FALSE,
    must_change_password BOOLEAN DEFAULT FALSE,
    status               TEXT DEFAULT 'active',
    area                 TEXT,
    created_at           TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (tenant_id, email)
);

CREATE TABLE IF NOT EXISTS {schema}.test_sessions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES {schema}.tenants(id),
    certification_id TEXT, user_email TEXT, num_questions INT, topics JSONB,
    ai_generated BOOLEAN DEFAULT FALSE, score_pct REAL, correct INT, total INT,
    passed BOOLEAN DEFAULT FALSE, repeated_questions INT DEFAULT 0,
    duration_sec REAL, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_tenant_user ON {schema}.test_sessions(tenant_id, user_email, created_at);

CREATE TABLE IF NOT EXISTS {schema}.test_answers (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES {schema}.tenants(id),
    session_id TEXT REFERENCES {schema}.test_sessions(id),
    question_id TEXT, topic TEXT, selected JSONB, is_correct BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_answers_session ON {schema}.test_answers(session_id);

CREATE TABLE IF NOT EXISTS {schema}.class_progress (
    tenant_id    TEXT NOT NULL REFERENCES {schema}.tenants(id),
    user_email   TEXT NOT NULL,
    class_id     TEXT NOT NULL,
    completed_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (tenant_id, user_email, class_id)
);

-- Log de acessos e atividades (auditoria para o admin do tenant).
CREATE TABLE IF NOT EXISTS {schema}.activity_log (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    user_email  TEXT NOT NULL,
    user_name   TEXT,
    action      TEXT NOT NULL,
    detail      JSONB,
    ip          TEXT,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_activity_tenant_time ON {schema}.activity_log(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_user ON {schema}.activity_log(tenant_id, user_email, created_at DESC);
"""


def _hash_pw(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _upsert_tenant(cur, schema, slug, name, color, logo, allow_reg=True) -> str:
    cur.execute(f"SELECT id FROM {schema}.tenants WHERE slug=%s", (slug,))
    r = cur.fetchone()
    if r:
        return r[0]
    tid = str(uuid.uuid4())
    cur.execute(
        f"INSERT INTO {schema}.tenants (id,slug,name,primary_color,logo_url,allow_self_register) "
        "VALUES (%s,%s,%s,%s,%s,%s)", (tid, slug, name, color, logo, allow_reg),
    )
    return tid


def _upsert_user(cur, schema, tid, email, name, pw_hash, is_admin=True) -> None:
    cur.execute(
        f"INSERT INTO {schema}.users (tenant_id,email,name,password_hash,is_admin) "
        "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (tenant_id,email) DO NOTHING",
        (tid, email.lower(), name, pw_hash, is_admin),
    )


def seed_with_connection(
    conn,
    *,
    schema: str = "certifica",
    platform_slug: str = "platform",
    superadmin_emails: Optional[Iterable[str]] = None,
    admin_password: str = "Certifica@2026",
    default_tenant_slug: str = "",
    default_tenant_name: str = "",
    default_tenant_color: str = "#2272B4",
    default_tenant_logo: str = "",
    log=print,
) -> dict:
    """Cria schema + banco global + tenants a partir de uma conexão psycopg já aberta.

    Devolve um resumo {certs, questions, flashcards, tenants, superadmins}.
    A conexão pode estar em autocommit ou não (o chamador faz commit se preciso).
    """
    superadmin_emails = [e.strip().lower() for e in (superadmin_emails or []) if e and e.strip()]
    data = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    certs, questions, flashcards = data["certifications"], data["questions"], data["flashcards"]

    log(f"[seed] criando schema/tabelas em '{schema}'...")
    conn.execute(DDL.format(schema=schema))

    with conn.cursor() as cur:
        for c in certs:
            cur.execute(
                f"INSERT INTO {schema}.certifications "
                "(id,name,type,level,description,exam_guide_url,topics,resources) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET "
                "name=EXCLUDED.name, topics=EXCLUDED.topics, resources=EXCLUDED.resources",
                (c["id"], c["name"], c.get("type"), c.get("level"), c.get("description"),
                 c.get("exam_guide_url"), json.dumps(c.get("topics", [])),
                 json.dumps(c.get("resources", []))),
            )
        for q in questions:
            cur.execute(
                f"INSERT INTO {schema}.questions (id,certification_id,topic,question_text,"
                "question_type,options,correct_answers,explanation,difficulty,is_ai_generated) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (q["id"], q["certification_id"], q.get("topic"), q["question_text"],
                 q.get("question_type", "multiple_choice"), json.dumps(q["options"]),
                 json.dumps(q["correct_answers"]), q.get("explanation", ""),
                 q.get("difficulty", 3), q.get("is_ai_generated", False)),
            )
        for f in flashcards:
            cur.execute(
                f"INSERT INTO {schema}.flashcards (id,certification_id,topic,front,back,difficulty) "
                "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (f["id"], f["certification_id"], f.get("topic"), f["front"], f["back"],
                 f.get("difficulty", 2)),
            )
        log(f"[seed] banco global: {len(certs)} certs / {len(questions)} q / {len(flashcards)} fc")

        # Tenant interno 'platform' (consola superadmin) — sempre criado.
        plat = _upsert_tenant(cur, schema, platform_slug, "Platform Console",
                              default_tenant_color, None, allow_reg=False)
        pw_hash = _hash_pw(admin_password) if superadmin_emails else None
        for em in superadmin_emails:
            _upsert_user(cur, schema, plat, em, em.split("@")[0], pw_hash, is_admin=True)

        created = {"platform": plat[:8]}
        # Primeiro tenant (cliente) — opcional.
        if default_tenant_slug:
            cust = _upsert_tenant(cur, schema, default_tenant_slug,
                                  default_tenant_name or default_tenant_slug.title(),
                                  default_tenant_color, default_tenant_logo or None)
            for em in superadmin_emails:
                _upsert_user(cur, schema, cust, em, em.split("@")[0], pw_hash, is_admin=True)
            created[default_tenant_slug] = cust[:8]

        log(f"[seed] tenants: {created}")
        log(f"[seed] superadmins: {superadmin_emails or '(nenhum)'}")

    return {
        "certs": len(certs), "questions": len(questions), "flashcards": len(flashcards),
        "tenants": created, "superadmins": superadmin_emails,
    }
