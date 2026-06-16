"""
Geração de novas questões via Foundation Model API (Claude Opus 4.8).

Em MOCK_MODE (sem Databricks) retorna questões sintéticas simples, para que a
flag "Gerar via IA" funcione no dev local sem chamar o endpoint.
"""
import json
import logging
import re
import uuid
from typing import List, Optional

from app.config import get_settings
from app.models.schemas import Certification, Question

logger = logging.getLogger(__name__)


_SYSTEM = (
    "You are an expert Databricks certification exam author. "
    "Generate high-quality practice questions that mirror the style of the "
    "official Databricks certification practice tests: scenario-based when "
    "possible, with one clearly correct answer and plausible distractors. "
    "Respond ONLY with a JSON array, no prose."
)


def _prompt(cert: Certification, count: int, topics: List[str],
            difficulty: Optional[int]) -> str:
    schema = (
        '[{"topic": "<one of the topics>", "question_text": "...", '
        '"question_type": "multiple_choice", '
        '"options": ["A","B","C","D"], "correct_answers": [<index>], '
        '"explanation": "...", "difficulty": <1-5>}]'
    )
    diff = f" Target difficulty: {difficulty}/5." if difficulty else ""
    return (
        f"Certification: {cert.name} ({cert.level}).\n"
        f"Description: {cert.description}\n"
        f"Allowed topics: {', '.join(topics)}.\n"
        f"Generate {count} NEW multiple-choice questions.{diff}\n"
        f"correct_answers is a list of 0-based indices into options "
        f"(usually one element; use multiple only for select-all questions).\n"
        f"Return JSON matching exactly this schema:\n{schema}"
    )


def _parse(raw: str, cert: Certification, topics: List[str]) -> List[Question]:
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    items = json.loads(m.group(0))
    out: List[Question] = []
    valid_topics = set(topics)
    for it in items:
        topic = it.get("topic")
        if topic not in valid_topics:
            topic = topics[0]
        opts = it.get("options") or []
        ca = it.get("correct_answers") or []
        ca = [i for i in ca if isinstance(i, int) and 0 <= i < len(opts)]
        if len(opts) < 2 or not ca:
            continue
        qtype = "multiple_select" if len(ca) > 1 else it.get("question_type", "multiple_choice")
        out.append(Question(
            id=f"ai_{cert.id}_{uuid.uuid4().hex[:8]}",
            certification_id=cert.id,
            topic=topic,
            question_text=it.get("question_text", "").strip(),
            question_type=qtype,
            options=opts,
            correct_answers=ca,
            explanation=it.get("explanation", "").strip(),
            difficulty=int(it.get("difficulty", 3)),
            is_ai_generated=True,
        ))
    return out


def _mock(cert: Certification, count: int, topics: List[str]) -> List[Question]:
    out = []
    for i in range(count):
        t = topics[i % len(topics)]
        out.append(Question(
            id=f"ai_{cert.id}_{uuid.uuid4().hex[:8]}",
            certification_id=cert.id, topic=t,
            question_text=f"[IA-mock] Questão de exemplo {i+1} sobre {t} ({cert.name}).",
            question_type="multiple_choice",
            options=["Opção correta de exemplo", "Distrator A", "Distrator B", "Distrator C"],
            correct_answers=[0],
            explanation="Questão gerada em modo mock (sem chamada ao LLM).",
            difficulty=3, is_ai_generated=True,
        ))
    return out


def generate_questions(certification: Certification, count: int,
                       topics: Optional[List[str]] = None,
                       difficulty: Optional[int] = None) -> List[Question]:
    s = get_settings()
    count = max(1, min(count, s.LLM_MAX_GENERATE))
    topics = topics or certification.topics

    if s.MOCK_MODE:
        logger.info("LLM em MOCK_MODE — gerando questões sintéticas")
        return _mock(certification, count, topics)

    from app.auth.workspace_client import get_workspace_client
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

    client = get_workspace_client()
    resp = client.serving_endpoints.query(
        name=s.LLM_ENDPOINT,
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content=_SYSTEM),
            ChatMessage(role=ChatMessageRole.USER,
                        content=_prompt(certification, count, topics, difficulty)),
        ],
        temperature=0.7,
        max_tokens=4000,
    )
    raw = resp.choices[0].message.content
    questions = _parse(raw, certification, topics)
    logger.info(f"LLM gerou {len(questions)} questões válidas via {s.LLM_ENDPOINT}")
    return questions
