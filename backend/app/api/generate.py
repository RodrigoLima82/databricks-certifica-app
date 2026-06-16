"""
Endpoint de geração de questões via LLM (Claude Opus 4.8 / Foundation Model API).
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import GenerateRequest, GenerateResponse, UserPublic
from app.config import get_settings
from app.auth import security
from app.services import repo
from app.services.llm_gen import generate_questions

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=GenerateResponse)
async def generate(req: GenerateRequest,
                   _: UserPublic = Depends(security.get_current_user)):
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

    source = "mock" if get_settings().MOCK_MODE else "llm"
    return GenerateResponse(success=True, questions=questions, source=source)
