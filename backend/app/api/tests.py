"""
Endpoints de simulado: montar e corrigir (protegidos por autenticação).
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import (
    TestSetupRequest, TestSession, TestSubmitRequest, TestResult, UserPublic,
)
from app.auth import security
from app.services import test_service

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


@router.post("/submit", response_model=TestResult)
async def submit_test(req: TestSubmitRequest,
                      user: UserPublic = Depends(security.get_current_user)):
    if not req.answers:
        raise HTTPException(422, "Nenhuma resposta enviada")
    return test_service.grade_test(req, user_email=user.email)
