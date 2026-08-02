"""
Testes do repositório (camada mock / seed em memória).
"""
from app.services import repo
from app.models.schemas import Question
from tests.conftest import ASSOC


def test_list_certifications():
    certs = repo.list_certifications()
    assert len(certs) == 6
    ids = {c.id for c in certs}
    assert ASSOC in ids


def test_get_certification_existente_e_inexistente():
    assert repo.get_certification(ASSOC) is not None
    assert repo.get_certification("nao_existe") is None


def test_questions_for_retorna_apenas_da_cert():
    qs = repo.questions_for(ASSOC)
    assert len(qs) > 0
    assert all(q.certification_id == ASSOC for q in qs)


def test_questions_for_filtra_por_topico():
    cert = repo.get_certification(ASSOC)
    topic = cert.topics[0]
    qs = repo.questions_for(ASSOC, topics=[topic])
    assert len(qs) > 0
    assert all(q.topic == topic for q in qs)


def test_flashcards_for():
    fs = repo.flashcards_for(ASSOC)
    assert len(fs) > 0
    assert all(f.certification_id == ASSOC for f in fs)


def test_add_questions_persiste_no_store():
    antes = len(repo.questions_for(ASSOC))
    nova = Question(
        id="test_unit_q1", certification_id=ASSOC, topic="ML Workflows",
        question_text="Pergunta de teste?", question_type="multiple_choice",
        options=["a", "b"], correct_answers=[0], explanation="", difficulty=2,
        is_ai_generated=True,
    )
    repo.add_questions([nova])
    depois = repo.questions_for(ASSOC)
    assert len(depois) == antes + 1
    assert any(q.id == "test_unit_q1" for q in depois)
