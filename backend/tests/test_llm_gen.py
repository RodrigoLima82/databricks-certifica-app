"""
Testes da geração via LLM: mock e parsing robusto da resposta do modelo.
"""
import json
from app.services import llm_gen
from app.services.repo import get_certification
from tests.conftest import ASSOC

CERT = get_certification(ASSOC)
TOPICS = CERT.topics


def test_mock_gera_quantidade_pedida():
    qs = llm_gen.generate_questions(CERT, count=4, topics=TOPICS)
    assert len(qs) == 4
    assert all(q.is_ai_generated for q in qs)
    assert all(q.certification_id == ASSOC for q in qs)
    assert all(q.topic in TOPICS for q in qs)


def test_mock_respeita_limite_maximo():
    qs = llm_gen.generate_questions(CERT, count=999, topics=TOPICS)
    assert len(qs) <= 10  # LLM_MAX_GENERATE


def test_parse_json_valido():
    raw = json.dumps([{
        "topic": TOPICS[0], "question_text": "Q?", "question_type": "multiple_choice",
        "options": ["a", "b", "c", "d"], "correct_answers": [2],
        "explanation": "pq sim", "difficulty": 3,
    }])
    qs = llm_gen._parse(raw, CERT, TOPICS)
    assert len(qs) == 1
    assert qs[0].correct_answers == [2] and qs[0].is_ai_generated


def test_parse_ignora_indice_fora_do_range():
    raw = json.dumps([{
        "topic": TOPICS[0], "question_text": "Q?", "options": ["a", "b"],
        "correct_answers": [5], "explanation": "", "difficulty": 2,
    }])
    # índice 5 inválido -> sem respostas válidas -> questão descartada
    assert llm_gen._parse(raw, CERT, TOPICS) == []


def test_parse_detecta_multiple_select():
    raw = json.dumps([{
        "topic": TOPICS[0], "question_text": "Q?", "options": ["a", "b", "c"],
        "correct_answers": [0, 2], "explanation": "", "difficulty": 4,
    }])
    qs = llm_gen._parse(raw, CERT, TOPICS)
    assert len(qs) == 1 and qs[0].question_type == "multiple_select"


def test_parse_topico_invalido_cai_no_primeiro():
    raw = json.dumps([{
        "topic": "Tópico Inexistente", "question_text": "Q?", "options": ["a", "b"],
        "correct_answers": [0], "explanation": "", "difficulty": 2,
    }])
    qs = llm_gen._parse(raw, CERT, TOPICS)
    assert len(qs) == 1 and qs[0].topic == TOPICS[0]


def test_parse_com_texto_em_volta_e_fences():
    raw = "Claro! Aqui estão:\n```json\n" + json.dumps([{
        "topic": TOPICS[1], "question_text": "Q?", "options": ["a", "b"],
        "correct_answers": [1], "explanation": "", "difficulty": 2,
    }]) + "\n```\nEspero ter ajudado."
    qs = llm_gen._parse(raw, CERT, TOPICS)
    assert len(qs) == 1 and qs[0].correct_answers == [1]


def test_parse_lixo_retorna_vazio():
    assert llm_gen._parse("desculpe, não consigo", CERT, TOPICS) == []
