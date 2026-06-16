"""
Cria o schema e popula o Lakebase (Postgres) com o banco de questões.

Uso (após `databricks auth login` e configurar o backend/.env com MOCK_MODE=false
e os parâmetros PG*/LAKEBASE_INSTANCE_NAME):

    cd backend && python -m seed.seed_lakebase

Idempotente: usa CREATE TABLE IF NOT EXISTS e ON CONFLICT DO NOTHING.
"""
import json
import logging
import sys
from pathlib import Path

# permite rodar como `python -m seed.seed_lakebase` a partir de backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.db import get_conn  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("seed")

SEED = Path(__file__).resolve().parent / "seed_data.json"

DDL = """
CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.certifications (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT,
    level           TEXT,
    description     TEXT,
    exam_guide_url  TEXT,
    topics          JSONB,
    resources       JSONB
);

CREATE TABLE IF NOT EXISTS {schema}.questions (
    id               TEXT PRIMARY KEY,
    certification_id TEXT NOT NULL REFERENCES {schema}.certifications(id),
    topic            TEXT,
    question_text    TEXT NOT NULL,
    question_type    TEXT NOT NULL DEFAULT 'multiple_choice',
    options          JSONB NOT NULL,
    correct_answers  JSONB NOT NULL,
    explanation      TEXT,
    difficulty       INT DEFAULT 3,
    is_ai_generated  BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_questions_cert ON {schema}.questions(certification_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic ON {schema}.questions(certification_id, topic);

CREATE TABLE IF NOT EXISTS {schema}.flashcards (
    id               TEXT PRIMARY KEY,
    certification_id TEXT NOT NULL REFERENCES {schema}.certifications(id),
    topic            TEXT,
    front            TEXT NOT NULL,
    back             TEXT NOT NULL,
    difficulty       INT DEFAULT 2
);
CREATE INDEX IF NOT EXISTS idx_flashcards_cert ON {schema}.flashcards(certification_id);

CREATE TABLE IF NOT EXISTS {schema}.users (
    email                 TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    password_hash         TEXT NOT NULL,
    must_change_password  BOOLEAN DEFAULT FALSE,
    created_at            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.test_sessions (
    id                 TEXT PRIMARY KEY,
    certification_id   TEXT,
    user_email         TEXT,
    num_questions      INT,
    topics             JSONB,
    ai_generated       BOOLEAN DEFAULT FALSE,
    score_pct          REAL,
    correct            INT,
    total              INT,
    passed             BOOLEAN DEFAULT FALSE,
    repeated_questions INT DEFAULT 0,
    duration_sec       REAL,
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON {schema}.test_sessions(user_email, created_at);

CREATE TABLE IF NOT EXISTS {schema}.test_answers (
    id          TEXT PRIMARY KEY,
    session_id  TEXT REFERENCES {schema}.test_sessions(id),
    question_id TEXT,
    topic       TEXT,
    selected    JSONB,
    is_correct  BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_answers_session ON {schema}.test_answers(session_id);
"""


def main():
    s = get_settings()
    if s.MOCK_MODE:
        log.error("MOCK_MODE=true — configure o .env para Lakebase antes de semear.")
        sys.exit(1)

    data = json.loads(SEED.read_text(encoding="utf-8"))
    certs, questions, flashcards = data["certifications"], data["questions"], data["flashcards"]
    schema = s.PGSCHEMA

    with get_conn() as conn:
        log.info(f"Criando schema/tabelas em '{schema}'...")
        conn.execute(DDL.format(schema=schema))

        with conn.cursor() as cur:
            for c in certs:
                cur.execute(
                    f"INSERT INTO {schema}.certifications "
                    "(id,name,type,level,description,exam_guide_url,topics,resources) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET "
                    "name=EXCLUDED.name, exam_guide_url=EXCLUDED.exam_guide_url, "
                    "topics=EXCLUDED.topics, resources=EXCLUDED.resources",
                    (c["id"], c["name"], c.get("type"), c.get("level"),
                     c.get("description"), c.get("exam_guide_url"),
                     json.dumps(c.get("topics", [])),
                     json.dumps(c.get("resources", []))),
                )
            log.info(f"  {len(certs)} certificações")

            for q in questions:
                cur.execute(
                    f"INSERT INTO {schema}.questions "
                    "(id,certification_id,topic,question_text,question_type,options,"
                    "correct_answers,explanation,difficulty,is_ai_generated) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                    (q["id"], q["certification_id"], q.get("topic"),
                     q["question_text"], q.get("question_type", "multiple_choice"),
                     json.dumps(q["options"]), json.dumps(q["correct_answers"]),
                     q.get("explanation", ""), q.get("difficulty", 3),
                     q.get("is_ai_generated", False)),
                )
            log.info(f"  {len(questions)} questões")

            for f in flashcards:
                cur.execute(
                    f"INSERT INTO {schema}.flashcards "
                    "(id,certification_id,topic,front,back,difficulty) "
                    "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                    (f["id"], f["certification_id"], f.get("topic"),
                     f["front"], f["back"], f.get("difficulty", 2)),
                )
            log.info(f"  {len(flashcards)} flashcards")

    log.info("Seed concluído com sucesso.")


if __name__ == "__main__":
    main()
