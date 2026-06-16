"""
Rastreamento: histórico de tentativas do usuário e visão geral do admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.models.schemas import (
    AttemptHistory, Attempt, AdminOverview, AdminUserRow, UserPublic,
    SessionDetail, AnswerDetail,
)
from app.auth import security
from app.services import repo, users as users_svc

router = APIRouter()


def _attempts_for(email: str, pass_mark: int) -> AttemptHistory:
    rows = repo.get_user_attempts(email)
    attempts = [Attempt(
        session_id=r["session_id"], certification_id=r["certification_id"],
        certification_name=r.get("certification_name"), score_pct=r["score_pct"],
        correct=r["correct"], total=r["total"], passed=r["passed"],
        ai_generated=r["ai_generated"], repeated_questions=r["repeated_questions"],
        created_at=r["created_at"],
    ) for r in rows]
    return AttemptHistory(user_email=email, pass_mark=pass_mark, attempts=attempts)


@router.get("/me/attempts", response_model=AttemptHistory)
async def my_attempts(user: UserPublic = Depends(security.get_current_user)):
    return _attempts_for(user.email, get_settings().PASS_MARK)


@router.get("/me/sessions/{session_id}", response_model=SessionDetail)
async def my_session_detail(session_id: str,
                            user: UserPublic = Depends(security.get_current_user)):
    # garante que a sessão pertence ao usuário
    owned = {a["session_id"] for a in repo.get_user_attempts(user.email)}
    if session_id not in owned:
        raise HTTPException(404, "Tentativa não encontrada")
    return SessionDetail(session_id=session_id,
                         answers=[AnswerDetail(**a) for a in repo.get_session_answers(session_id)])


# ── Admin: drill-down por usuário ──────────────────────────────────────────────
@router.get("/admin/users/{email}/attempts", response_model=AttemptHistory)
async def admin_user_attempts(email: str, _: UserPublic = Depends(security.require_admin)):
    return _attempts_for(email.lower(), get_settings().PASS_MARK)


@router.get("/admin/sessions/{session_id}", response_model=SessionDetail)
async def admin_session_detail(session_id: str, _: UserPublic = Depends(security.require_admin)):
    return SessionDetail(session_id=session_id,
                         answers=[AnswerDetail(**a) for a in repo.get_session_answers(session_id)])


def _build_pdf(session_id: str) -> Response:
    from app.services.pdf_report import build_attempt_pdf
    meta = repo.get_session_meta(session_id)
    if not meta:
        raise HTTPException(404, "Tentativa não encontrada")
    answers = repo.get_session_answers(session_id)
    pdf = build_attempt_pdf(meta, answers, get_settings().PASS_MARK)
    fname = f"simulado_{meta.get('user_email','aluno').split('@')[0]}_{session_id[:8]}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/admin/sessions/{session_id}/pdf")
async def admin_session_pdf(session_id: str, _: UserPublic = Depends(security.require_admin)):
    return _build_pdf(session_id)


@router.get("/me/sessions/{session_id}/pdf")
async def my_session_pdf(session_id: str, user: UserPublic = Depends(security.get_current_user)):
    owned = {a["session_id"] for a in repo.get_user_attempts(user.email)}
    if session_id not in owned:
        raise HTTPException(404, "Tentativa não encontrada")
    return _build_pdf(session_id)


@router.get("/admin/overview", response_model=AdminOverview)
async def admin_overview(_: UserPublic = Depends(security.require_admin)):
    s = get_settings()
    rows = repo.get_admin_overview()
    users = [AdminUserRow(
        email=r["email"], name=r["name"], attempts=r["attempts"],
        best_score=r["best_score"], last_score=r["last_score"],
        passed_any=r["passed_any"], last_attempt_at=r["last_attempt_at"],
    ) for r in rows]
    total_attempts = sum(u.attempts for u in users)
    return AdminOverview(pass_mark=s.PASS_MARK, total_users=len(users),
                         total_attempts=total_attempts, users=users)
