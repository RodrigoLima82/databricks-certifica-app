"""
Testes da montagem e correção de simulados — o núcleo da lógica.
"""
import pytest
from app.services import test_service
from app.models.schemas import (
    TestSetupRequest, TestSubmitRequest, AnswerSubmission,
)
from tests.conftest import ASSOC


# ── build_test ────────────────────────────────────────────────────────────────
def test_build_respeita_num_questions():
    s = test_service.build_test(TestSetupRequest(certification_id=ASSOC, num_questions=10))
    assert len(s.questions) == 10
    assert s.num_questions == 10


def test_build_sem_duplicatas():
    s = test_service.build_test(TestSetupRequest(certification_id=ASSOC, num_questions=30))
    ids = [q.id for q in s.questions]
    assert len(ids) == len(set(ids))


def test_build_filtra_topico():
    cert = test_service.repo.get_certification(ASSOC)
    topic = cert.topics[0]
    s = test_service.build_test(
        TestSetupRequest(certification_id=ASSOC, num_questions=5, topics=[topic])
    )
    assert all(q.topic == topic for q in s.questions)


def test_build_com_ia_inclui_geradas():
    s = test_service.build_test(TestSetupRequest(
        certification_id=ASSOC, num_questions=8, ai_generate=True, ai_count=3,
    ))
    assert s.ai_generated is True
    gen = [q for q in s.questions if q.is_ai_generated]
    assert len(gen) >= 1
    # questões geradas devem estar persistidas para a correção encontrá-las
    pool_ids = {q.id for q in test_service.repo.questions_for(ASSOC)}
    assert all(q.id in pool_ids for q in gen)


def test_build_cert_invalida_levanta():
    with pytest.raises(ValueError):
        test_service.build_test(TestSetupRequest(certification_id="xxx", num_questions=5))


# ── grade_test ────────────────────────────────────────────────────────────────
def _answers(session, fn):
    return [AnswerSubmission(question_id=q.id, selected=fn(q)) for q in session.questions]


def test_grade_tudo_certo():
    s = test_service.build_test(TestSetupRequest(certification_id=ASSOC, num_questions=10))
    req = TestSubmitRequest(
        session_id=s.id, certification_id=ASSOC,
        answers=_answers(s, lambda q: q.correct_answers), duration_sec=60,
    )
    r = test_service.grade_test(req)
    assert r.correct == 10 and r.total == 10 and r.score_pct == 100.0


def test_grade_tudo_errado():
    s = test_service.build_test(TestSetupRequest(certification_id=ASSOC, num_questions=10))
    def wrong(q):
        n = len(q.options)
        return [(q.correct_answers[0] + 1) % n]
    req = TestSubmitRequest(
        session_id=s.id, certification_id=ASSOC, answers=_answers(s, wrong),
    )
    r = test_service.grade_test(req)
    assert r.correct == 0 and r.score_pct == 0.0


def test_grade_parcial_e_por_topico():
    s = test_service.build_test(TestSetupRequest(certification_id=ASSOC, num_questions=10))
    # acerta metade
    ans = []
    for i, q in enumerate(s.questions):
        if i % 2 == 0:
            ans.append(AnswerSubmission(question_id=q.id, selected=q.correct_answers))
        else:
            n = len(q.options)
            ans.append(AnswerSubmission(question_id=q.id, selected=[(q.correct_answers[0] + 1) % n]))
    r = test_service.grade_test(TestSubmitRequest(session_id=s.id, certification_id=ASSOC, answers=ans))
    assert r.correct == 5
    # soma dos tópicos = total
    assert sum(t.total for t in r.by_topic) == r.total
    assert sum(t.correct for t in r.by_topic) == r.correct


def test_grade_multiple_select_exige_conjunto_exato():
    # acha uma questão multiple_select no banco
    qs = test_service.repo.questions_for(ASSOC)
    ms = next((q for q in qs if q.question_type == "multiple_select"), None)
    if ms is None:
        pytest.skip("sem multiple_select nessa cert")
    # resposta parcial (só a primeira correta) deve contar como ERRADA
    s_id = "sess-ms"
    req = TestSubmitRequest(session_id=s_id, certification_id=ASSOC, answers=[
        AnswerSubmission(question_id=ms.id, selected=[ms.correct_answers[0]])
    ])
    r = test_service.grade_test(req)
    assert r.correct == 0
    # resposta completa conta como certa
    req2 = TestSubmitRequest(session_id=s_id, certification_id=ASSOC, answers=[
        AnswerSubmission(question_id=ms.id, selected=list(reversed(ms.correct_answers)))
    ])
    r2 = test_service.grade_test(req2)
    assert r2.correct == 1  # ordem não importa
