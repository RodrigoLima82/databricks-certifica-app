"""
Geração via Foundation Model API (Claude Opus 4.8 / gpt-oss-120b).

Alinhado com o "AI Prep Guide: Any Databricks Certification" (Databricks, 2026):
o prompt de sistema aplica as salvaguardas anti-alucinação da guia — usar apenas
nomes de produto ATUAIS, não inventar objetivos, ancorar em docs oficiais — e
injeta a tabela de produtos renomeados (Step 3 da guia).

Além de gerar questões (Diagnose/Practice), expõe funções para o loop de estudo:
- repair_wrong_answers ...... Step 4.5 (explicar erros)
- deep_dive_objective ....... Step 4.3 (ensinar um objetivo)
- hands_on_checklist ........ Step 5 (tarefas práticas)

Em MOCK_MODE retorna respostas sintéticas para o dev local sem chamar o endpoint.
"""
import json
import logging
import re
import uuid
from typing import List, Optional

from app.config import get_settings
from app.models.schemas import Certification, Question

logger = logging.getLogger(__name__)


# ── Tabela de produtos renomeados (AI Prep Guide, Step 3) ─────────────────────
# A IA foi treinada antes das mudanças recentes da plataforma e usa nomes antigos
# com confiança. Injetamos os mais comuns no prompt para bloquear o erro nº 1.
_RENAMED_PRODUCTS = [
    ("Delta Live Tables (DLT)", "Lakeflow Declarative Pipelines"),
    ("Databricks Workflows / Jobs", "Lakeflow Jobs"),
    ("Partner Connect ingestion / Arcion", "Lakeflow Connect"),
    ("Databricks SQL Analytics", "Databricks SQL"),
    ("Databricks Runtime for ML notebooks", "Databricks Machine Learning"),
    ("Feature Store (standalone)", "Unity Catalog feature engineering"),
    ("Model Registry (workspace)", "Unity Catalog Model Registry / MLflow 3"),
    ("Databricks Repos", "Git folders"),
    ("Databricks Assistant (old branding)", "Databricks Assistant / Genie"),
]

_GUIDE_RULES = (
    "Follow these rules strictly (from the official Databricks AI Prep Guide):\n"
    "1. Use ONLY current Databricks product names and behaviors. Never use "
    "deprecated names as if current.\n"
    "2. Do NOT invent objectives, features, or products that are not part of "
    "the certification scope.\n"
    "3. Ground everything in official Databricks sources (docs.databricks.com "
    "and Databricks Academy) — never third-party blogs, tutorials or forums.\n"
    "4. If you are not certain a fact is current and correct per the official "
    "docs, do not present it as fact.\n"
    "Renamed products — always prefer the CURRENT name (old -> current):\n"
    + "\n".join(f"   - {old}  ->  {new}" for old, new in _RENAMED_PRODUCTS)
)


_SYSTEM = (
    "You are an expert Databricks certification exam author and tutor. "
    "Generate high-quality practice questions that mirror the style of the "
    "official Databricks certification practice tests: scenario-based when "
    "possible, with one clearly correct answer and plausible distractors.\n"
    + _GUIDE_RULES +
    "\nRespond ONLY with a JSON array, no prose."
)

# Sistema para os fluxos de tutoria (repair / deep-dive / hands-on).
_TUTOR_SYSTEM = (
    "You are an expert Databricks certification tutor helping a candidate "
    "prepare. Be precise, concise and practical.\n" + _GUIDE_RULES
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


def _extract_text(content) -> str:
    """Normaliza o `content` da resposta do LLM para texto.

    Claude Opus retorna string. Modelos com raciocínio (ex.: gpt-oss-120b)
    retornam uma lista de blocos [{type: 'reasoning'|'text', ...}]; nesse
    caso concatenamos apenas os blocos de texto (ignorando o raciocínio).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content or "")


_DIFFICULTY_WORDS = {
    "easy": 2, "medium": 3, "moderate": 3, "hard": 4, "difficult": 4,
    "beginner": 1, "intermediate": 3, "advanced": 5, "expert": 5,
}


def _coerce_difficulty(val, default: int = 3) -> int:
    """Aceita int, string numérica ('4') ou rótulo ('Medium')."""
    if isinstance(val, (int, float)):
        return max(1, min(5, int(val)))
    if isinstance(val, str):
        v = val.strip().lower()
        if v.isdigit():
            return max(1, min(5, int(v)))
        if v in _DIFFICULTY_WORDS:
            return _DIFFICULTY_WORDS[v]
    return default


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
            difficulty=_coerce_difficulty(it.get("difficulty", 3)),
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


def _chat(system: str, user: str, max_tokens: int = 4000) -> str:
    """Chamada genérica ao endpoint de serving. Retorna o texto da resposta.

    Reutilizada por todos os fluxos (gerar questões, repair, deep-dive,
    hands-on). Omitimos `temperature` de propósito: alguns modelos da FMAPI
    (ex.: Claude Opus 4.x) rejeitam o parâmetro com BAD_REQUEST.
    """
    from app.auth.workspace_client import get_workspace_client
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

    client = get_workspace_client()
    resp = client.serving_endpoints.query(
        name=get_settings().LLM_ENDPOINT,
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content=system),
            ChatMessage(role=ChatMessageRole.USER, content=user),
        ],
        max_tokens=max_tokens,
    )
    return _extract_text(resp.choices[0].message.content)


def _parse_json(raw: str):
    """Extrai o primeiro objeto/array JSON do texto (tolerante a prosa/markdown)."""
    m = re.search(r"\{.*\}|\[.*\]", raw, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def generate_questions(certification: Certification, count: int,
                       topics: Optional[List[str]] = None,
                       difficulty: Optional[int] = None) -> List[Question]:
    s = get_settings()
    count = max(1, min(count, s.LLM_MAX_GENERATE))
    topics = topics or certification.topics

    if s.MOCK_MODE:
        logger.info("LLM em MOCK_MODE — gerando questões sintéticas")
        return _mock(certification, count, topics)

    raw = _chat(_SYSTEM, _prompt(certification, count, topics, difficulty))
    questions = _parse(raw, certification, topics)
    logger.info(f"LLM gerou {len(questions)} questões válidas via {s.LLM_ENDPOINT}")
    return questions


# ── Step 4.4: simulado completo (full mock exam) ──────────────────────────────
# A guia pede "a full mock exam matching the number of scored questions specified
# in the exam guide, distributed across the objectives in the proportions the
# guide implies". Usamos cert_info (nº real de questões + pesos por domínio).

def allocate_by_weight(total: int, weights: List[float]) -> List[int]:
    """Reparte `total` questões entre domínios proporcionalmente a `weights`,
    via largest-remainder (Hamilton): soma exatamente `total`, cada domínio com
    peso > 0 recebe ao menos 1 questão."""
    n = len(weights)
    if n == 0 or total <= 0:
        return [0] * n
    wsum = sum(weights)
    if wsum <= 0:  # sem pesos → distribuição uniforme
        base, rem = divmod(total, n)
        return [base + (1 if i < rem else 0) for i in range(n)]

    exact = [total * w / wsum for w in weights]
    floors = [int(x) for x in exact]
    # garante mínimo 1 por domínio com peso positivo (se couber)
    for i, w in enumerate(weights):
        if w > 0 and floors[i] == 0:
            floors[i] = 1
    # ajusta para somar exatamente `total`
    diff = total - sum(floors)
    if diff > 0:  # distribui sobrras aos maiores restos
        order = sorted(range(n), key=lambda i: exact[i] - int(exact[i]), reverse=True)
        for k in range(diff):
            floors[order[k % n]] += 1
    elif diff < 0:  # remove excesso dos que têm mais (sem zerar peso positivo)
        order = sorted(range(n), key=lambda i: floors[i], reverse=True)
        k = 0
        while diff < 0:
            i = order[k % n]
            if floors[i] > (1 if weights[i] > 0 else 0):
                floors[i] -= 1
                diff += 1
            k += 1
    return floors


def build_mock_exam(certification: Certification, domains: List[dict],
                    total: int) -> tuple[List[Question], List[dict]]:
    """Gera um simulado completo de `total` questões distribuídas pelos `domains`
    (cada um {name, weight|None}) nas proporções do exam guide. Gera por domínio
    (em lotes de até LLM_MAX_GENERATE) e devolve (questões, distribuição).
    `distribution` = [{domain, requested, generated}] para transparência na UI.

    Gera os domínios em PARALELO (ThreadPoolExecutor): cada domínio é uma tarefa
    que faz seus lotes internos. Sem isso, 45q em ~7 domínios seriam ~7 chamadas
    sequenciais ao LLM (minutos) e estouram o timeout do frontend."""
    from concurrent.futures import ThreadPoolExecutor

    s = get_settings()
    weights = [float(d.get("weight") or 0) for d in domains]
    alloc = allocate_by_weight(total, weights)

    # Achata em lotes (domínio, batch_size): domínios grandes viram vários lotes.
    # Todos os lotes rodam concorrentes → latência ~= 1 chamada ao LLM, não N.
    batches: List[tuple] = []
    for d, want in zip(domains, alloc):
        name = d.get("name", "")
        remaining = want
        while remaining > 0:
            b = min(remaining, s.LLM_MAX_GENERATE)
            batches.append((name, b))
            remaining -= b

    def _gen_batch(name: str, batch: int) -> tuple:
        if s.MOCK_MODE:
            return name, _mock(certification, batch, [name])
        try:
            raw = _chat(_SYSTEM, _domain_prompt(certification, name, batch))
            return name, _parse_domain(raw, certification, name)
        except Exception as e:
            logger.warning(f"Falha ao gerar lote do domínio '{name}': {e}")
            return name, []

    by_domain: dict = {d.get("name", ""): [] for d in domains}

    def _run(bs: List[tuple]) -> None:
        if not bs:
            return
        workers = min(len(bs), 12) or 1
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for name, got in ex.map(lambda t: _gen_batch(*t), bs):
                by_domain[name].extend(got)

    _run(batches)
    max_workers = min(len(batches), 12) if batches else 0

    # Top-up: um lote gerado pode devolver menos questões válidas que o pedido
    # (parse descarta malformadas). Uma 2ª tentativa cobre os domínios em déficit.
    if not s.MOCK_MODE:
        want_by = {d.get("name", ""): w for d, w in zip(domains, alloc)}
        topup = [(n, want_by[n] - len(by_domain[n]))
                 for n in want_by if len(by_domain[n]) < want_by[n]]
        topup = [(n, min(deficit, s.LLM_MAX_GENERATE)) for n, deficit in topup if deficit > 0]
        _run(topup)

    questions: List[Question] = []
    distribution: List[dict] = []
    for d, want in zip(domains, alloc):
        name = d.get("name", "")
        got = by_domain[name][:want]
        questions.extend(got)
        distribution.append({"domain": name, "requested": want, "generated": len(got)})

    logger.info(
        f"Mock exam {certification.id}: pedido {total}, gerado {len(questions)} "
        f"em {len(domains)} domínios (paralelo x{max_workers}) via {s.LLM_ENDPOINT}"
    )
    return questions, distribution


def _domain_prompt(cert: Certification, domain: str, count: int) -> str:
    schema = (
        '[{"topic": "<domain>", "question_text": "...", '
        '"question_type": "multiple_choice", '
        '"options": ["A","B","C","D"], "correct_answers": [<index>], '
        '"explanation": "...", "difficulty": <1-5>}]'
    )
    return (
        f"Certification: {cert.name} ({cert.level}).\n"
        f"Exam-guide domain / objective group: \"{domain}\".\n"
        f"Generate {count} NEW scenario-based multiple-choice questions that assess "
        f"ONLY this domain, matching the style and difficulty of the real Databricks "
        f"certification exam. Use the field \"topic\" set to the domain name above.\n"
        f"correct_answers is a list of 0-based indices into options "
        f"(usually one element; use multiple only for select-all questions).\n"
        f"Return JSON matching exactly this schema:\n{schema}"
    )


def _parse_domain(raw: str, cert: Certification, domain: str) -> List[Question]:
    """Como _parse, mas o `topic` é sempre o nome do domínio (não valida contra
    o banco de tópicos, pois os domínios do exam guide são um eixo distinto)."""
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except Exception:
        return []
    out: List[Question] = []
    for it in items:
        opts = it.get("options") or []
        ca = it.get("correct_answers") or []
        ca = [i for i in ca if isinstance(i, int) and 0 <= i < len(opts)]
        if len(opts) < 2 or not ca:
            continue
        qtype = "multiple_select" if len(ca) > 1 else it.get("question_type", "multiple_choice")
        out.append(Question(
            id=f"ai_{cert.id}_{uuid.uuid4().hex[:8]}",
            certification_id=cert.id,
            topic=domain,
            question_text=it.get("question_text", "").strip(),
            question_type=qtype,
            options=opts,
            correct_answers=ca,
            explanation=it.get("explanation", "").strip(),
            difficulty=_coerce_difficulty(it.get("difficulty", 3)),
            is_ai_generated=True,
        ))
    return out


# ── Loop de estudo do AI Prep Guide ───────────────────────────────────────────

def repair_wrong_answers(certification: Certification,
                         wrong: List[dict]) -> List[dict]:
    """Step 4.5 — para cada questão errada: explica o equívoco, por que a
    resposta certa é certa, e dá uma questão relacionada que testa o mesmo
    conceito de outra forma. `wrong` = [{question_text, options, correct_answers,
    selected, explanation, topic}]. Retorna lista de dicts de repair."""
    if get_settings().MOCK_MODE:
        return [{
            "topic": w.get("topic", ""),
            "question_text": w.get("question_text", ""),
            "misconception": "[mock] Equívoco de exemplo.",
            "why_correct": "[mock] A resposta correta é correta porque...",
            "related_question": "[mock] Pergunta relacionada de exemplo.",
        } for w in wrong]

    payload = [{
        "topic": w.get("topic"),
        "question_text": w.get("question_text"),
        "options": w.get("options"),
        "correct_index": w.get("correct_answers"),
        "my_answer_index": w.get("selected"),
    } for w in wrong]
    user = (
        f"Certification: {certification.name} ({certification.level}).\n"
        "The candidate got these questions wrong. For EACH, return an object "
        "with: topic, question_text (echo it), misconception (what likely "
        "confused them), why_correct (why the correct option is correct), "
        "related_question (a NEW question testing the same concept "
        "differently, plain text).\n"
        f"Questions:\n{json.dumps(payload, ensure_ascii=False)}\n"
        'Respond ONLY with a JSON array: [{"topic":"...","question_text":"...",'
        '"misconception":"...","why_correct":"...","related_question":"..."}]'
    )
    data = _parse_json(_chat(_TUTOR_SYSTEM, user)) or []
    return data if isinstance(data, list) else []


def deep_dive_objective(certification: Certification, objective: str) -> dict:
    """Step 4.3 — ensina um objetivo específico: conceito central, como
    funciona no Databricks, quando usar vs. alternativas, erros comuns e um
    exemplo de código executável. Retorna dict."""
    if get_settings().MOCK_MODE:
        return {
            "objective": objective,
            "core_concept": "[mock] Conceito central.",
            "how_it_works": "[mock] Como funciona no Databricks.",
            "when_to_use": "[mock] Quando usar vs. alternativas.",
            "common_mistakes": "[mock] Erros comuns.",
            "code_example": "# [mock] exemplo",
            "doc_url": "https://docs.databricks.com/",
        }
    # B1 — grounding: allowlist de páginas oficiais (docs.databricks.com/llms.txt)
    from app.services.docs_grounding import sources_block, official_sources
    query = f"{objective} {certification.name}"
    allowlist = sources_block(query, k=8)

    user = (
        f"Certification: {certification.name} ({certification.level}).\n"
        f"Teach me this objective: \"{objective}\".\n"
        "Use ONLY official Databricks documentation and Databricks Academy. "
        + (allowlist + "\n" if allowlist else
           "Include a real docs.databricks.com URL in doc_url (not a guess — if "
           "unsure, use the closest official docs section).\n")
        + 'Respond ONLY with a JSON object: {"objective":"...","core_concept":'
        '"...","how_it_works":"...","when_to_use":"...","common_mistakes":"...",'
        '"code_example":"...","doc_url":"https://docs.databricks.com/..."}'
    )
    out = _parse_json(_chat(_TUTOR_SYSTEM, user)) or {}

    # Defesa em profundidade: se o doc_url não estiver na allowlist, troca pela
    # página oficial mais relevante (evita URL alucinada mesmo se o modelo ignorar).
    if out and isinstance(out, dict):
        hits = official_sources(query, k=8)
        allowed = {url for _, url in hits}
        url = (out.get("doc_url") or "").strip()
        if hits and url not in allowed:
            out["doc_url"] = hits[0][1]
    return out


def hands_on_checklist(certification: Certification) -> List[dict]:
    """Step 5 (CRÍTICO) — 6 a 10 tarefas práticas que o candidato deve saber
    executar antes do exame, cada uma mapeada a um objetivo e pequena o
    suficiente para < 30 min no Free Edition. Cada tarefa inclui um passo-a-passo
    curto (`steps`) de COMO fazer e um `doc_url` oficial (grounding B1)."""
    if get_settings().MOCK_MODE:
        return [{
            "task": f"[mock] Tarefa prática {i+1}.",
            "objective": (certification.topics or ["geral"])[i % max(1, len(certification.topics or [1]))],
            "est_minutes": 20,
            "steps": ["[mock] Passo 1", "[mock] Passo 2", "[mock] Passo 3"],
            "doc_url": "https://docs.databricks.com/",
        } for i in range(6)]

    # B1 — grounding: allowlist de páginas oficiais para os doc_url das tarefas.
    from app.services.docs_grounding import sources_block, official_sources
    topics = ", ".join(certification.topics or [])
    allowlist = sources_block(f"{certification.name} {topics}", k=12)

    user = (
        f"Certification: {certification.name} ({certification.level}).\n"
        f"Objectives/topics: {topics}.\n"
        "List 6-10 hands-on tasks I should be able to perform fluently before "
        "sitting this exam. Each task must be small enough to complete in under "
        "30 minutes in Databricks Free Edition or a free trial, and map to an "
        "objective. For EACH task also give:\n"
        "- steps: 3-6 short imperative steps on HOW to do it in the Databricks UI "
        "or with code (concrete: menus, commands, SQL/PySpark snippets).\n"
        "- doc_url: the single most relevant official docs.databricks.com page.\n"
        + (allowlist + "\n" if allowlist else "") +
        'Respond ONLY with a JSON array: [{"task":"one sentence","objective":'
        '"which objective it maps to","est_minutes":<int 5-30>,'
        '"steps":["step 1","step 2","..."],"doc_url":"https://docs.databricks.com/..."}]'
    )
    data = _parse_json(_chat(_TUTOR_SYSTEM, user)) or []
    if not isinstance(data, list):
        return []

    # Defesa em profundidade: doc_url fora da allowlist → troca pela oficial mais
    # relevante ao texto da tarefa (evita link alucinado).
    hits = official_sources(f"{certification.name} {topics}", k=12)
    allowed = {url for _, url in hits}
    for it in data:
        if not isinstance(it, dict):
            continue
        url = (it.get("doc_url") or "").strip()
        if hits and url not in allowed:
            task_hits = official_sources(f"{it.get('task','')} {it.get('objective','')}", k=1)
            it["doc_url"] = task_hits[0][1] if task_hits else hits[0][1]
        if not isinstance(it.get("steps"), list):
            it["steps"] = []
    return data


def match_topics_to_classes(certification: Certification,
                            topics: List[str],
                            classes: List[dict]) -> dict:
    """Associa cada tópico fraco às aulas da trilha que o cobrem (erro→treinamento).
    `classes` = [{id,title,type,duration,url,route_name}]. Retorna
    {topic: [class_id, ...]} — os ids das aulas mais relevantes por tópico.

    A trilha usa nomes de curso e o exame usa domínios; nem sempre batem por
    texto, então usamos a IA para mapear semanticamente."""
    if not topics or not classes:
        return {}
    if get_settings().MOCK_MODE:
        # mock: associa cada tópico à 1ª aula (determinístico p/ dev)
        return {t: [classes[0]["id"]] for t in topics if classes and classes[0].get("id")}

    catalog = [{"id": c.get("id"), "title": c.get("title"),
                "route": c.get("route_name", "")} for c in classes if c.get("id")]
    user = (
        f"Certification: {certification.name} ({certification.level}).\n"
        "Map each WEAK EXAM TOPIC to the training classes that best cover it. "
        "Pick 1-3 class ids per topic from the catalog; if none fits a topic, "
        "return an empty list for it. Match by subject, not by exact words.\n"
        f"Weak topics: {json.dumps(topics, ensure_ascii=False)}\n"
        f"Class catalog: {json.dumps(catalog, ensure_ascii=False)}\n"
        'Respond ONLY with a JSON object mapping topic -> [class_id,...]: '
        '{"<topic>":["<class_id>",...]}'
    )
    data = _parse_json(_chat(_TUTOR_SYSTEM, user))
    if not isinstance(data, dict):
        return {}
    # sanitiza: só ids válidos, tópicos conhecidos
    valid_ids = {c.get("id") for c in classes if c.get("id")}
    known = set(topics)
    out = {}
    for t, ids in data.items():
        if t in known and isinstance(ids, list):
            out[t] = [i for i in ids if i in valid_ids][:3]
    return out
