"""
Endpoints de certificações, questões e flashcards.
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Header
from typing import List, Optional

from app.models.schemas import Certification, Question, Flashcard, UserPublic, CertInfo
from app.auth import security
from app.services import repo
from app.services.cert_info import get_cert_info, resolve_lang

router = APIRouter()


@router.get("/", response_model=List[Certification])
async def list_certifications():
    return repo.list_certifications()


@router.get("/{certification_id}/info", response_model=CertInfo)
async def certification_info(certification_id: str,
                            _: UserPublic = Depends(security.get_current_user),
                            accept_language: Optional[str] = Header(default=None)):
    info = get_cert_info(certification_id, resolve_lang(accept_language))
    if not info:
        raise HTTPException(404, "Sem informações de exame para esta certificação")
    return CertInfo(**info)


@router.get("/{certification_id}", response_model=Certification)
async def get_certification(certification_id: str):
    cert = repo.get_certification(certification_id)
    if not cert:
        raise HTTPException(404, "Certificação não encontrada")
    return cert


@router.get("/{certification_id}/questions", response_model=List[Question])
async def get_questions(
    certification_id: str,
    topics: Optional[List[str]] = Query(default=None),
    _: UserPublic = Depends(security.get_current_user),
):
    if not repo.get_certification(certification_id):
        raise HTTPException(404, "Certificação não encontrada")
    return repo.questions_for(certification_id, topics)


@router.get("/{certification_id}/flashcards", response_model=List[Flashcard])
async def get_flashcards(
    certification_id: str,
    topics: Optional[List[str]] = Query(default=None),
    _: UserPublic = Depends(security.get_current_user),
):
    if not repo.get_certification(certification_id):
        raise HTTPException(404, "Certificação não encontrada")
    return repo.flashcards_for(certification_id, topics)
