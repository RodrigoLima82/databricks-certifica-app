"""
Repositório de dados — abstrai Lakebase (Postgres) vs seed em memória (mock).

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


# ── Sessões de simulado (persistência + rastreamento) ─────────────────────────
def seen_question_ids(user_email: str, certification_id: str) -> set:
    """IDs de questões que o usuário já respondeu em tentativas anteriores (para repetição)."""
    if not _use_db() or not user_email:
        return set()
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT a.question_id FROM test_answers a "
            "JOIN test_sessions s ON s.id = a.session_id "
            "WHERE s.user_email=%s AND s.certification_id=%s",
            (user_email, certification_id),
        ).fetchall()
    return {r[0] for r in rows}


def save_test_result(result: TestResult, user_email: Optional[str],
                     ai_generated: bool, topics: List[str],
                     passed: bool = False, repeated_questions: int = 0) -> None:
    """Grava sessão + respostas no Lakebase (coleta de simulações + rastreamento)."""
    if not _use_db():
        return
    from app.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO test_sessions (id,certification_id,user_email,num_questions,"
                "topics,ai_generated,score_pct,correct,total,passed,repeated_questions,"
                "duration_sec) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (id) DO NOTHING",
                (result.session_id, result.certification_id, user_email,
                 result.total, json.dumps(topics), ai_generated,
                 result.score_pct, result.correct, result.total, passed,
                 repeated_questions, result.duration_sec),
            )
            for a in result.results:
                cur.execute(
                    "INSERT INTO test_answers (id,session_id,question_id,topic,selected,"
                    "is_correct) VALUES (%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), result.session_id, a.question_id, a.topic,
                     json.dumps(a.selected), a.is_correct),
                )


def get_user_attempts(user_email: str) -> List[dict]:
    if not _use_db():
        return []
    from app.db import get_conn
    names = {c.id: c.name for c in list_certifications()}
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id,certification_id,score_pct,correct,total,passed,ai_generated,"
            "repeated_questions,created_at FROM test_sessions "
            "WHERE user_email=%s ORDER BY created_at DESC", (user_email,),
        ).fetchall()
    return [{
        "session_id": r[0], "certification_id": r[1],
        "certification_name": names.get(r[1]), "score_pct": r[2], "correct": r[3],
        "total": r[4], "passed": r[5], "ai_generated": r[6],
        "repeated_questions": r[7], "created_at": r[8].isoformat() if r[8] else None,
    } for r in rows]


def get_session_meta(session_id: str) -> Optional[dict]:
    """Metadados de uma tentativa (para cabeçalho de export)."""
    if not _use_db():
        return None
    from app.db import get_conn
    names = {c.id: c.name for c in list_certifications()}
    with get_conn() as conn:
        r = conn.execute(
            "SELECT s.id, s.user_email, COALESCE(u.name, s.user_email) AS name, "
            "s.certification_id, s.score_pct, s.correct, s.total, s.passed, "
            "s.repeated_questions, s.duration_sec, s.created_at "
            "FROM test_sessions s LEFT JOIN users u ON u.email = s.user_email "
            "WHERE s.id=%s", (session_id,),
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


def get_session_answers(session_id: str) -> List[dict]:
    """Respostas detalhadas de uma tentativa (join com a questão)."""
    if not _use_db():
        return []
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT a.question_id, a.topic, a.selected, a.is_correct, "
            "q.question_text, q.options, q.correct_answers, q.explanation, q.is_ai_generated "
            "FROM test_answers a LEFT JOIN questions q ON q.id = a.question_id "
            "WHERE a.session_id=%s", (session_id,),
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


def get_admin_overview() -> List[dict]:
    if not _use_db():
        return []
    from app.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT u.email, u.name, COUNT(s.id) AS attempts, MAX(s.score_pct) AS best, "
            "BOOL_OR(s.passed) AS passed_any, MAX(s.created_at) AS last_at, "
            "(SELECT score_pct FROM test_sessions s2 WHERE s2.user_email=u.email "
            " ORDER BY created_at DESC LIMIT 1) AS last_score "
            "FROM users u LEFT JOIN test_sessions s ON s.user_email=u.email "
            "GROUP BY u.email, u.name ORDER BY attempts DESC, u.name",
        ).fetchall()
    return [{
        "email": r[0], "name": r[1], "attempts": r[2], "best_score": r[3],
        "passed_any": bool(r[4]), "last_attempt_at": r[5].isoformat() if r[5] else None,
        "last_score": r[6],
    } for r in rows]
