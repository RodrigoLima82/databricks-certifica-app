"""
Endpoints de geração via LLM (Foundation Model API) — alinhados com o
"AI Prep Guide: Any Databricks Certification":
- POST /            → questões (Diagnose/Practice)
- POST /repair      → explicar erros (Step 4.5)
- POST /deep-dive   → ensinar um objetivo (Step 4.3)
- POST /hands-on/{certification_id} → checklist prático (Step 5)
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Request

from app.models.schemas import (
    GenerateRequest, GenerateResponse, UserPublic,
    RepairRequest, RepairResponse, RepairItem,
    DeepDiveRequest, DeepDiveResponse,
    HandsOnResponse, HandsOnTask,
)
from app.config import get_settings
from app.auth import security
from app.services import repo, activity
from app.services.llm_gen import (
    generate_questions, repair_wrong_answers, deep_dive_objective,
    hands_on_checklist,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _source() -> str:
    return "mock" if get_settings().MOCK_MODE else "llm"


@router.post("/", response_model=GenerateResponse)
async def generate(req: GenerateRequest, request: Request,
                   user: UserPublic = Depends(security.get_current_user)):
    cert = repo.get_certification(req.certification_id)
    if not cert:
        raise HTTPException(404, "Certificação não encontrada")
    try:
        questions = generate_questions(
            certification=cert, count=req.count,
            topics=req.topics, difficulty=req.difficulty,
        )
    except Exception as e:
        logger.error(f"Erro na geração: {e}")
        return GenerateResponse(success=False, source="error", message=str(e))

    if req.persist and questions:
        try:
            repo.add_questions(questions)
        except Exception as e:
            logger.warning(f"Não foi possível persistir questões geradas: {e}")

    activity.log_event(
        user.tenant_id, user.email, "question_generate", request=request, user_name=user.name,
        detail={"certification_id": req.certification_id, "count": len(questions),
                "topics": req.topics or []},
    )
    return GenerateResponse(success=True, questions=questions, source=_source())


@router.post("/repair", response_model=RepairResponse)
async def repair(req: RepairRequest,
                 _: UserPublic = Depends(security.get_current_user)):
    """Step 4.5 — explica cada resposta errada + questão relacionada."""
    cert = repo.get_certification(req.certification_id)
    if not cert:
        raise HTTPException(404, "Certificação não encontrada")
    if not req.wrong:
        return RepairResponse(success=True, items=[], source=_source())
    try:
        raw = repair_wrong_answers(cert, [w.model_dump() for w in req.wrong])
    except Exception as e:
        logger.error(f"Erro no repair: {e}")
        return RepairResponse(success=False, source="error", message=str(e))
    items = [RepairItem(**{k: v for k, v in it.items() if k in RepairItem.model_fields})
             for it in raw]
    return RepairResponse(success=True, items=items, source=_source())


@router.post("/deep-dive", response_model=DeepDiveResponse)
async def deep_dive(req: DeepDiveRequest,
                    _: UserPublic = Depends(security.get_current_user)):
    """Step 4.3 — ensina um objetivo específico com fontes oficiais."""
    cert = repo.get_certification(req.certification_id)
    if not cert:
        raise HTTPException(404, "Certificação não encontrada")
    if not req.objective.strip():
        raise HTTPException(422, "Objetivo obrigatório")
    try:
        d = deep_dive_objective(cert, req.objective.strip())
    except Exception as e:
        logger.error(f"Erro no deep-dive: {e}")
        return DeepDiveResponse(success=False, source="error", message=str(e))
    d = {k: v for k, v in (d or {}).items() if k in DeepDiveResponse.model_fields}
    return DeepDiveResponse(success=True, source=_source(), **d)


@router.post("/hands-on/{certification_id}", response_model=HandsOnResponse)
async def hands_on(certification_id: str,
                   _: UserPublic = Depends(security.get_current_user)):
    """Step 5 (CRÍTICO) — checklist de tarefas práticas por certificação."""
    cert = repo.get_certification(certification_id)
    if not cert:
        raise HTTPException(404, "Certificação não encontrada")
    try:
        raw = hands_on_checklist(cert)
    except Exception as e:
        logger.error(f"Erro no hands-on: {e}")
        return HandsOnResponse(success=False, certification_id=certification_id,
                               source="error", message=str(e))
    tasks = [HandsOnTask(**{k: v for k, v in t.items() if k in HandsOnTask.model_fields})
             for t in raw if t.get("task")]
    return HandsOnResponse(success=True, certification_id=certification_id,
                           tasks=tasks, source=_source())
