"""
Plano de estudo adaptativo: foca os pontos fracos do usuário e os associa à
trilha de treinamento (erro → curso), medindo melhora até dominar o tópico.

Fonte de dados: todas as tentativas do usuário (test_answers agregadas por
tópico em repo.topic_mastery). Cada tópico recebe um status:
  - weak       : pct < pass_mark
  - improving  : pass_mark <= pct < mastery_mark
  - mastered   : pct >= mastery_mark
E as aulas da trilha que cobrem os tópicos fracos/improving são associadas via
IA (llm_gen.match_topics_to_classes).
"""
import logging
from typing import Optional

from app.config import get_settings
from app.models.schemas import (
    StudyPlanResponse, StudyPlanTopic, StudyPlanClass,
)
from app.services import repo, tenants as tenants_svc

logger = logging.getLogger(__name__)

MASTERY_MARK = 80   # % para considerar um tópico dominado


def _trend(first: float, recent: float) -> str:
    if recent - first >= 5:
        return "up"
    if first - recent >= 5:
        return "down"
    return "flat"


def _status(pct: float, pass_mark: int) -> str:
    if pct >= MASTERY_MARK:
        return "mastered"
    if pct >= pass_mark:
        return "improving"
    return "weak"


def build_study_plan(tenant_id: str, tenant_slug: str, user_email: str,
                     certification_id: str) -> StudyPlanResponse:
    pass_mark = get_settings().PASS_MARK
    mastery = repo.topic_mastery(tenant_id, user_email, certification_id)

    if not mastery:
        return StudyPlanResponse(
            certification_id=certification_id, mastery_mark=MASTERY_MARK,
            pass_mark=pass_mark, attempts_count=0, topics=[], source="none",
            message="",  # vazio → o frontend usa o texto i18n (plan.empty) no idioma do usuário
        )

    # nº de provas feitas nesta cert (para contexto)
    attempts_rows = [a for a in repo.get_user_attempts(tenant_id, user_email)
                     if a["certification_id"] == certification_id]

    topics: list[StudyPlanTopic] = []
    for m in mastery:
        st = _status(m["pct"], pass_mark)
        topics.append(StudyPlanTopic(
            topic=m["topic"], correct=m["correct"], total=m["total"], pct=m["pct"],
            recent_pct=m["recent_pct"], first_pct=m["first_pct"], attempts=m["attempts"],
            status=st, trend=_trend(m["first_pct"], m["recent_pct"]), classes=[],
        ))

    # Aulas da trilha desta cert (para associar aos tópicos que não estão dominados)
    routes = tenants_svc.get_routes(tenant_slug or "").get("routes", [])
    classes: list[dict] = []
    for r in routes:
        if r.get("certification_id") and r["certification_id"] != certification_id:
            continue
        for c in r.get("classes", []):
            if c.get("id"):
                classes.append({
                    "id": c["id"], "title": c.get("title", ""),
                    "type": c.get("type", "elearning"), "duration": c.get("duration", ""),
                    "url": c.get("url"), "route_name": r.get("name", ""),
                })

    weak_topics = [t.topic for t in topics if t.status != "mastered"]
    source = "none"
    if weak_topics and classes:
        try:
            from app.services.llm_gen import match_topics_to_classes
            from app.services.repo import get_certification
            cert = get_certification(certification_id)
            mapping = match_topics_to_classes(cert, weak_topics, classes) if cert else {}
            source = "mock" if get_settings().MOCK_MODE else "llm"
            by_id = {c["id"]: c for c in classes}
            for t in topics:
                for cid in mapping.get(t.topic, []):
                    c = by_id.get(cid)
                    if c:
                        t.classes.append(StudyPlanClass(**c))
        except Exception as e:
            logger.warning(f"Falha ao associar tópicos à trilha: {e}")
            source = "error"

    return StudyPlanResponse(
        certification_id=certification_id, mastery_mark=MASTERY_MARK,
        pass_mark=pass_mark, attempts_count=len(attempts_rows), topics=topics,
        source=source,
    )
