"""
Montagem e correção de simulados.
"""
import logging
import random
import uuid
from typing import List

from app.models.schemas import (
    TestSetupRequest, TestSession, Question, TestSubmitRequest, TestResult,
    AnswerResult, TopicScore,
)
from app.services import repo

logger = logging.getLogger(__name__)


def build_test(req: TestSetupRequest) -> TestSession:
    cert = repo.get_certification(req.certification_id)
    if not cert:
        raise ValueError(f"Certificação não encontrada: {req.certification_id}")

    topics = req.topics or cert.topics
    pool = repo.questions_for(req.certification_id, topics)

    selected: List[Question] = []
    ai_used = False

    # Questões geradas via LLM (opcional)
    if req.ai_generate and req.ai_count > 0:
        try:
            from app.services.llm_gen import generate_questions
            gen = generate_questions(
                certification=cert, count=min(req.ai_count, 10), topics=topics,
            )
            if gen:
                # persiste para que a correção encontre as questões e para coletá-las
                try:
                    repo.add_questions(gen)
                except Exception as e:
                    logger.warning(f"Não foi possível persistir questões geradas: {e}")
            selected.extend(gen)
            ai_used = len(gen) > 0
        except Exception as e:
            logger.warning(f"Falha na geração via LLM, seguindo só com o banco: {e}")

    # Completa com questões do banco (sem repetir as geradas)
    remaining = max(req.num_questions - len(selected), 0)
    bank = [q for q in pool if q.id not in {s.id for s in selected}]
    random.shuffle(bank)
    selected.extend(bank[:remaining])

    random.shuffle(selected)
    selected = selected[: req.num_questions]

    return TestSession(
        id=str(uuid.uuid4()),
        certification_id=req.certification_id,
        questions=selected,
        num_questions=len(selected),
        topics=topics,
        ai_generated=ai_used,
    )


def grade_test(req: TestSubmitRequest, user_email: str | None = None) -> TestResult:
    from app.config import get_settings
    # repetição: questões desta sessão que o usuário já viu antes
    answered_ids = {a.question_id for a in req.answers}
    seen_before = repo.seen_question_ids(user_email, req.certification_id) if user_email else set()
    repeated = len(answered_ids & seen_before)

    pool = {q.id: q for q in repo.questions_for(req.certification_id)}
    # Inclui geradas em runtime que possam não estar no pool persistido
    results: List[AnswerResult] = []
    topic_acc: dict[str, list[int]] = {}

    for ans in req.answers:
        q = pool.get(ans.question_id)
        if not q:
            continue
        correct = sorted(ans.selected) == sorted(q.correct_answers)
        results.append(AnswerResult(
            question_id=q.id, topic=q.topic, selected=ans.selected,
            correct_answers=q.correct_answers, is_correct=correct,
        ))
        c, t = topic_acc.setdefault(q.topic, [0, 0])
        topic_acc[q.topic] = [c + (1 if correct else 0), t + 1]

    total = len(results)
    correct_n = sum(1 for r in results if r.is_correct)
    by_topic = [TopicScore(topic=t, correct=v[0], total=v[1])
                for t, v in sorted(topic_acc.items())]

    pass_mark = get_settings().PASS_MARK
    score_pct = round(100 * correct_n / total, 1) if total else 0.0
    result = TestResult(
        session_id=req.session_id,
        certification_id=req.certification_id,
        score_pct=score_pct,
        correct=correct_n,
        total=total,
        answered=total,
        passed=score_pct >= pass_mark,
        pass_mark=pass_mark,
        repeated_questions=repeated,
        duration_sec=req.duration_sec,
        by_topic=by_topic,
        results=results,
    )

    passed = result.passed
    try:
        repo.save_test_result(result, user_email, ai_generated=False, topics=[],
                              passed=passed, repeated_questions=repeated)
    except Exception as e:
        logger.warning(f"Não foi possível persistir a sessão: {e}")

    return result
