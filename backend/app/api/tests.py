"""
Endpoints de simulado: montar e corrigir (protegidos por autenticação).
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from fastapi import Request

from app.models.schemas import (
    TestSetupRequest, TestSession, TestSubmitRequest, TestResult, UserPublic,
    MockExamRequest,
)
from app.auth import security
from app.services import test_service, activity

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=TestSession)
async def create_test(req: TestSetupRequest,
                      _: UserPublic = Depends(security.get_current_user)):
    try:
        session = test_service.build_test(req)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not session.questions:
        raise HTTPException(422, "Nenhuma questão disponível para os filtros escolhidos")
    return session


@router.post("/mock", response_model=TestSession)
async def create_mock_exam(req: MockExamRequest,
                           _: UserPublic = Depends(security.get_current_user)):
    """Step 4.4 — simulado completo: nº real de questões do exam guide,
    distribuído pelos domínios nas proporções oficiais."""
    try:
        session = test_service.build_mock_exam(req.certification_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not session.questions:
        raise HTTPException(502, "Não foi possível gerar o simulado (LLM). Tente novamente.")
    return session


@router.post("/submit", response_model=TestResult)
async def submit_test(req: TestSubmitRequest, request: Request,
                      user: UserPublic = Depends(security.get_current_user)):
    if not req.answers:
        raise HTTPException(422, "Nenhuma resposta enviada")
    result = test_service.grade_test(req, tenant_id=user.tenant_id, user_email=user.email)
    activity.log_event(
        user.tenant_id, user.email, "test_submit", request=request, user_name=user.name,
        detail={"certification_id": result.certification_id, "score_pct": result.score_pct,
                "correct": result.correct, "total": result.total, "passed": result.passed},
    )
    return result
