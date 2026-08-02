"""
Repositório de dados — abstrai RDS (Postgres) vs seed em memória (mock).

A escolha é por MOCK_MODE: em dev tudo vem do seed; em produção, do Postgres.
"""
import json
import logging
import uuid
from typing import List, Optional

from app.config import get_settings
from app.models.schemas import (
    Certification, Question, Flashcard, TestResult, TopicScore, AnswerResult,
)
from app.services.store import get_store

logger = logging.getLogger(__name__)


def _use_db() -> bool:
    return not get_settings().MOCK_MODE


# ── Certificações ─────────────────────────────────────────────────────────────
def list_certifications() -> List[Certification]:
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id,name,type,level,description,exam_guide_url,topics,resources "
                "FROM certifications ORDER BY type, level"
            ).fetchall()
        def _j(v):
            return v if isinstance(v, list) else json.loads(v or "[]")
        return [
            Certification(
                id=r[0], name=r[1], type=r[2], level=r[3], description=r[4],
                exam_guide_url=r[5], topics=_j(r[6]), resources=_j(r[7]),
            )
            for r in rows
        ]
    return [Certification(**c) for c in get_store().list_certifications()]


def get_certification(cid: str) -> Optional[Certification]:
    return next((c for c in list_certifications() if c.id == cid), None)


# ── Questões ──────────────────────────────────────────────────────────────────
def _row_to_question(r) -> Question:
    return Question(
        id=r[0], certification_id=r[1], topic=r[2], question_text=r[3],
        question_type=r[4],
        options=r[5] if isinstance(r[5], list) else json.loads(r[5]),
        correct_answers=r[6] if isinstance(r[6], list) else json.loads(r[6]),
        explanation=r[7] or "", difficulty=r[8] or 3, is_ai_generated=r[9],
    )


def questions_for(cid: str, topics: Optional[List[str]] = None) -> List[Question]:
    if _use_db():
        from app.db import get_conn
        sql = (
            "SELECT id,certification_id,topic,question_text,question_type,options,"
            "correct_answers,explanation,difficulty,is_ai_generated "
            "FROM questions WHERE certification_id=%s"
        )
        params: list = [cid]
        if topics:
            sql += " AND topic = ANY(%s)"
            params.append(topics)
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_question(r) for r in rows]

    qs = [Question(**q) for q in get_store().questions_for(cid)]
    if topics:
        qs = [q for q in qs if q.topic in topics]
    return qs


def add_questions(questions: List[Question]):
    """Persiste questões (ex.: geradas via LLM)."""
    if _use_db():
        from app.db import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                for q in questions:
                    cur.execute(
                        "INSERT INTO questions (id,certification_id,topic,question_text,"
                        "question_type,options,correct_answers,explanation,difficulty,"
                        "is_ai_generated) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                        "ON CONFLICT (id) DO NOTHING",
                        (q.id, q.certification_id, q.topic, q.question_text,
                         q.question_type, json.dumps(q.options),
                         json.dumps(q.correct_answers), q.explanation,
                         q.difficulty, q.is_ai_generated),
                    )
        return
    get_store().add_questions([q.model_dump() for q in questions])


# ── Flashcards ─────────────────────────────────────────────────────────────────
def flashcards_for(cid: str, topics: Optional[List[str]] = None) -> List[Flashcard]:
    if _use_db():
        from app.db import get_conn
        sql = ("SELECT id,certification_id,topic,front,back,difficulty "
               "FROM flashcards WHERE certification_id=%s")
        params: list = [cid]
        if topics:
            sql += " AND topic = ANY(%s)"
            params.append(topics)
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [Flashcard(id=r[0], certification_id=r[1], topic=r[2],
                          front=r[3], back=r[4], difficulty=r[5] or 2) for r in rows]
    fs = [Flashcard(**f) for f in get_store().flashcards_for(cid)]
    if topics:
        fs = [f for f in fs if f.topic in topics]
    return fs


# ── Sessões de simulado (persistência + rastreamento) — escopo por tenant ─────
def seen_question_ids(tenant_id: str, user_email: str, certification_id: str) -> set:
    """IDs de questões já respondidas por este usuário/tenant (para detectar repetição)."""
    if not _use_db() or not user_email:
        return set()
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT a.question_id FROM test_answers a "
            "JOIN test_sessions s ON s.id = a.session_id "
            "WHERE s.tenant_id=%s AND s.user_email=%s AND s.certification_id=%s",
            (tenant_id, user_email, certification_id),
        ).fetchall()
    return {r[0] for r in rows}


def save_test_result(result: TestResult, tenant_id: str, user_email: Optional[str],
                     ai_generated: bool, topics: List[str],
                     passed: bool = False, repeated_questions: int = 0) -> None:
    """Grava sessão + respostas (coleta de simulações + rastreamento), por tenant."""
    if not _use_db():
        return
    from app.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO test_sessions (id,tenant_id,certification_id,user_email,"
                "num_questions,topics,ai_generated,score_pct,correct,total,passed,"
                "repeated_questions,duration_sec) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (result.session_id, tenant_id, result.certification_id, user_email,
                 result.total, json.dumps(topics), ai_generated,
                 result.score_pct, result.correct, result.total, passed,
                 repeated_questions, result.duration_sec),
            )
            for a in result.results:
                cur.execute(
                    "INSERT INTO test_answers (id,tenant_id,session_id,question_id,topic,"
                    "selected,is_correct) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, result.session_id, a.question_id,
                     a.topic, json.dumps(a.selected), a.is_correct),
                )


def get_user_attempts(tenant_id: str, user_email: str) -> List[dict]:
    if not _use_db():
        return []
    from app.db import get_conn
    names = {c.id: c.name for c in list_certifications()}
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id,certification_id,score_pct,correct,total,passed,ai_generated,"
            "repeated_questions,created_at FROM test_sessions "
            "WHERE tenant_id=%s AND user_email=%s ORDER BY created_at DESC",
            (tenant_id, user_email),
        ).fetchall()
    return [{
        "session_id": r[0], "certification_id": r[1],
        "certification_name": names.get(r[1]), "score_pct": r[2], "correct": r[3],
        "total": r[4], "passed": r[5], "ai_generated": r[6],
        "repeated_questions": r[7], "created_at": r[8].isoformat() if r[8] else None,
    } for r in rows]


def get_session_meta(tenant_id: str, session_id: str) -> Optional[dict]:
    """Metadados de uma tentativa (para cabeçalho de export), escopado por tenant."""
    if not _use_db():
        return None
    from app.db import get_conn
    names = {c.id: c.name for c in list_certifications()}
    with get_conn() as conn:
        r = conn.execute(
            "SELECT s.id, s.user_email, COALESCE(u.name, s.user_email) AS name, "
            "s.certification_id, s.score_pct, s.correct, s.total, s.passed, "
            "s.repeated_questions, s.duration_sec, s.created_at "
            "FROM test_sessions s LEFT JOIN users u "
            "  ON u.email = s.user_email AND u.tenant_id = s.tenant_id "
            "WHERE s.id=%s AND s.tenant_id=%s", (session_id, tenant_id),
        ).fetchone()
    if not r:
        return None
    return {
        "session_id": r[0], "user_email": r[1], "user_name": r[2],
        "certification_id": r[3], "certification_name": names.get(r[3], r[3]),
        "score_pct": r[4], "correct": r[5], "total": r[6], "passed": r[7],
        "repeated_questions": r[8], "duration_sec": r[9],
        "created_at": r[10].isoformat() if r[10] else None,
    }


def get_session_answers(tenant_id: str, session_id: str) -> List[dict]:
    """Respostas detalhadas de uma tentativa (join com a questão), escopado por tenant."""
    if not _use_db():
        return []
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT a.question_id, a.topic, a.selected, a.is_correct, "
            "q.question_text, q.options, q.correct_answers, q.explanation, q.is_ai_generated "
            "FROM test_answers a LEFT JOIN questions q ON q.id = a.question_id "
            "WHERE a.session_id=%s AND a.tenant_id=%s", (session_id, tenant_id),
        ).fetchall()

    def _j(v):
        if v is None:
            return []
        return v if isinstance(v, list) else json.loads(v)

    return [{
        "question_id": r[0], "topic": r[1], "selected": _j(r[2]), "is_correct": r[3],
        "question_text": r[4] or "(questão não encontrada)",
        "options": _j(r[5]), "correct_answers": _j(r[6]),
        "explanation": r[7] or "", "is_ai_generated": bool(r[8]),
    } for r in rows]


def topic_mastery(tenant_id: str, user_email: str, certification_id: str) -> List[dict]:
    """Domínio por tópico agregando TODAS as tentativas do usuário nesta cert.
    Para cada tópico: correct/total acumulados + tendência (acerto na tentativa
    mais recente vs. a mais antiga). Ordena do mais fraco ao mais forte.
    Retorna [{topic, correct, total, pct, recent_pct, first_pct, attempts}]."""
    if not _use_db():
        return []
    from app.db import get_conn
    with get_conn() as conn:
        # acumulado por tópico (todas as respostas)
        agg = conn.execute(
            "SELECT a.topic, "
            "  COUNT(*) FILTER (WHERE a.is_correct) AS correct, "
            "  COUNT(*) AS total "
            "FROM test_answers a JOIN test_sessions s ON s.id = a.session_id "
            "WHERE a.tenant_id=%s AND s.user_email=%s AND s.certification_id=%s "
            "GROUP BY a.topic", (tenant_id, user_email, certification_id),
        ).fetchall()
        # tendência: % por tópico na 1ª e na última sessão em que o tópico apareceu
        trend = conn.execute(
            "WITH t AS ("
            "  SELECT a.topic, s.created_at, "
            "    COUNT(*) FILTER (WHERE a.is_correct)::float / NULLIF(COUNT(*),0) AS pct "
            "  FROM test_answers a JOIN test_sessions s ON s.id = a.session_id "
            "  WHERE a.tenant_id=%s AND s.user_email=%s AND s.certification_id=%s "
            "  GROUP BY a.topic, s.created_at) "
            "SELECT topic, "
            "  (ARRAY_AGG(pct ORDER BY created_at ASC))[1] AS first_pct, "
            "  (ARRAY_AGG(pct ORDER BY created_at DESC))[1] AS recent_pct, "
            "  COUNT(*) AS attempts "
            "FROM t GROUP BY topic",
            (tenant_id, user_email, certification_id),
        ).fetchall()
    tmap = {r[0]: {"first_pct": r[1], "recent_pct": r[2], "attempts": r[3]} for r in trend}
    out = []
    for topic, correct, total in agg:
        pct = round(100 * correct / total, 1) if total else 0.0
        tr = tmap.get(topic, {})
        out.append({
            "topic": topic, "correct": correct, "total": total, "pct": pct,
            "recent_pct": round(100 * tr["recent_pct"], 1) if tr.get("recent_pct") is not None else pct,
            "first_pct": round(100 * tr["first_pct"], 1) if tr.get("first_pct") is not None else pct,
            "attempts": tr.get("attempts", 1),
        })
    out.sort(key=lambda x: (x["pct"], -x["total"]))   # mais fraco primeiro
    return out


def get_leaderboard(tenant_id: str) -> List[dict]:
    """Ranking del tenant a partir de datos reales.
    Puntos = suma del mejor score (%) por certificación + 5 por clase completada."""
    if not _use_db():
        return []
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT u.email, u.name, u.area, "
            "  COALESCE(ROUND(SUM(c.best)::numeric, 0), 0) + 5*COALESCE(MAX(cp.cnt), 0) AS points, "
            "  COUNT(*) FILTER (WHERE c.passed) AS passed, "
            "  COALESCE(SUM(c.attempts), 0) AS attempts, "
            "  COALESCE(MAX(cp.cnt), 0) AS classes "
            "FROM users u "
            "LEFT JOIN ("
            "  SELECT user_email, certification_id, MAX(score_pct) AS best, "
            "         BOOL_OR(passed) AS passed, COUNT(*) AS attempts "
            "  FROM test_sessions WHERE tenant_id=%s GROUP BY user_email, certification_id"
            ") c ON c.user_email = u.email "
            "LEFT JOIN ("
            "  SELECT user_email, COUNT(*) AS cnt FROM class_progress "
            "  WHERE tenant_id=%s GROUP BY user_email"
            ") cp ON cp.user_email = u.email "
            "WHERE u.tenant_id=%s "
            "GROUP BY u.email, u.name, u.area "
            "ORDER BY points DESC, passed DESC, u.name", (tenant_id, tenant_id, tenant_id),
        ).fetchall()
    return [{"email": r[0], "name": r[1], "area": r[2],
             "points": float(r[3]), "passed": r[4], "attempts": r[5], "classes": r[6]} for r in rows]


# ── Progreso de clases (rutas de aprendizaje) ─────────────────────────────────
def get_class_progress(tenant_id: str, user_email: str) -> set:
    if not _use_db():
        return set()
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT class_id FROM class_progress WHERE tenant_id=%s AND user_email=%s",
            (tenant_id, user_email),
        ).fetchall()
    return {r[0] for r in rows}


def passed_certs(tenant_id: str, user_email: str) -> set:
    if not _use_db():
        return set()
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT certification_id FROM test_sessions "
            "WHERE tenant_id=%s AND user_email=%s AND passed=TRUE",
            (tenant_id, user_email),
        ).fetchall()
    return {r[0] for r in rows}


def mark_class(tenant_id: str, user_email: str, class_id: str) -> None:
    if not _use_db():
        return
    from app.db import get_conn
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO class_progress (tenant_id,user_email,class_id) VALUES (%s,%s,%s) "
            "ON CONFLICT (tenant_id,user_email,class_id) DO NOTHING",
            (tenant_id, user_email, class_id),
        )


def unmark_class(tenant_id: str, user_email: str, class_id: str) -> None:
    if not _use_db():
        return
    from app.db import get_conn
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM class_progress WHERE tenant_id=%s AND user_email=%s AND class_id=%s",
            (tenant_id, user_email, class_id),
        )


def get_admin_overview(tenant_id: str) -> List[dict]:
    if not _use_db():
        return []
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT u.email, u.name, COUNT(s.id) AS attempts, MAX(s.score_pct) AS best, "
            "BOOL_OR(s.passed) AS passed_any, MAX(s.created_at) AS last_at, "
            "(SELECT score_pct FROM test_sessions s2 WHERE s2.user_email=u.email "
            "  AND s2.tenant_id=u.tenant_id ORDER BY created_at DESC LIMIT 1) AS last_score, "
            "u.area, u.status, u.is_admin "
            "FROM users u LEFT JOIN test_sessions s "
            "  ON s.user_email=u.email AND s.tenant_id=u.tenant_id "
            "WHERE u.tenant_id=%s "
            "GROUP BY u.tenant_id, u.email, u.name, u.area, u.status, u.is_admin "
            "ORDER BY attempts DESC, u.name", (tenant_id,),
        ).fetchall()
    return [{
        "email": r[0], "name": r[1], "attempts": r[2], "best_score": r[3],
        "passed_any": bool(r[4]), "last_attempt_at": r[5].isoformat() if r[5] else None,
        "last_score": r[6], "area": r[7], "status": r[8] or "active", "is_admin": bool(r[9]),
    } for r in rows]
