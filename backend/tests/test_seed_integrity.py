"""
Valida a integridade do banco de questões (seed_data.json).
Garante que toda questão é consistente antes de ir para o Lakebase.
"""
import pytest
from app.services.store import get_store

store = get_store()
CERT_IDS = {c["id"] for c in store.certifications}
VALID_TYPES = {"multiple_choice", "multiple_select", "true_false"}


def test_seed_carregou():
    assert len(store.certifications) == 6
    assert len(store.questions) >= 600
    assert len(store.flashcards) >= 190


def test_certificacoes_tem_campos_obrigatorios():
    for c in store.certifications:
        assert c["id"] and c["name"] and c["level"] in ("associate", "professional")
        assert isinstance(c["topics"], list) and len(c["topics"]) >= 3
        assert c.get("exam_guide_url", "").startswith("https://www.databricks.com/")


@pytest.mark.parametrize("q", store.questions, ids=lambda q: q["id"])
def test_questao_valida(q):
    assert q["certification_id"] in CERT_IDS
    assert q["question_text"].strip()
    assert q["question_type"] in VALID_TYPES
    opts = q["options"]
    assert isinstance(opts, list) and len(opts) >= 2
    ca = q["correct_answers"]
    assert isinstance(ca, list) and len(ca) >= 1
    # todos os índices de resposta apontam para uma opção existente
    for i in ca:
        assert isinstance(i, int) and 0 <= i < len(opts), f"índice inválido em {q['id']}"
    # multiple_select deve ter >1 resposta; demais exatamente 1
    if q["question_type"] == "multiple_select":
        assert len(ca) >= 2
    else:
        assert len(ca) == 1
    assert 1 <= q["difficulty"] <= 5


def test_ids_unicos():
    ids = [q["id"] for q in store.questions]
    assert len(ids) == len(set(ids)), "há IDs de questão duplicados"


def test_topicos_das_questoes_existem_na_cert():
    by_cert = {c["id"]: set(c["topics"]) for c in store.certifications}
    for q in store.questions:
        assert q["topic"] in by_cert[q["certification_id"]], \
            f"tópico '{q['topic']}' não pertence a {q['certification_id']}"


@pytest.mark.parametrize("f", store.flashcards, ids=lambda f: f["id"])
def test_flashcard_valido(f):
    assert f["certification_id"] in CERT_IDS
    assert f["front"].strip() and f["back"].strip()
