"""
Rastreamento: histórico de tentativas do usuário e visão geral do admin (por tenant).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Header
from fastapi.responses import Response

from app.config import get_settings
import re
import logging

from app.models.schemas import (
    AttemptHistory, Attempt, AdminOverview, AdminUserRow, UserPublic,
    SessionDetail, AnswerDetail, UserProfileUpdate, UserStatusUpdate, AdminPasswordSet,
    AdminCreateUser, LeaderboardRow, ProgramProgress,
    StudyPlanResponse, TopicQuizRequest, TestSession,
    ActivityLog, ActivityEvent,
)
from app.auth import security
from app.services import repo, users as users_svc, tenants as tenants_svc, study_plan, activity

logger = logging.getLogger(__name__)
router = APIRouter()
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _attempts_for(tenant_id: str, email: str, pass_mark: int) -> AttemptHistory:
    rows = repo.get_user_attempts(tenant_id, email)
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
    return _attempts_for(user.tenant_id, user.email, get_settings().PASS_MARK)


@router.get("/leaderboard", response_model=list[LeaderboardRow])
async def leaderboard(user: UserPublic = Depends(security.get_current_user)):
    rows = repo.get_leaderboard(user.tenant_id)
    return [LeaderboardRow(rank=i + 1, **r) for i, r in enumerate(rows)]


@router.get("/me/program-progress", response_model=ProgramProgress)
async def my_program_progress(user: UserPublic = Depends(security.get_current_user)):
    routes = tenants_svc.get_routes(user.tenant_slug or "").get("routes", [])
    class_ids = {c.get("id") for r in routes for c in r.get("classes", []) if c.get("id")}
    target_certs = {r.get("certification_id") for r in routes if r.get("certification_id")}
    done = repo.get_class_progress(user.tenant_id, user.email) & class_ids
    passed = repo.passed_certs(user.tenant_id, user.email) & target_certs
    ct, pt = len(class_ids), len(target_certs)
    total = ct + pt
    pct = round(100 * (len(done) + len(passed)) / total) if total else 0
    return ProgramProgress(percent=pct, classes_done=len(done), classes_total=ct,
                           certs_passed=len(passed), certs_total=pt)


# ── Plano de estudo adaptativo (foco nos pontos fracos + trilha) ────────────────
@router.get("/me/study-plan/{certification_id}", response_model=StudyPlanResponse)
async def my_study_plan(certification_id: str,
                        user: UserPublic = Depends(security.get_current_user)):
    """Ranking de tópicos do mais fraco ao mais forte + aulas da trilha que os
    cobrem + status (weak/improving/mastered). Foca o estudo onde o usuário
    foi mal, até dominar (≥ mastery_mark)."""
    return study_plan.build_study_plan(
        user.tenant_id, user.tenant_slug or "", user.email, certification_id,
    )


@router.post("/me/topic-quiz", response_model=TestSession)
async def my_topic_quiz(req: TopicQuizRequest,
                        user: UserPublic = Depends(security.get_current_user)):
    """Mini-teste focado num único tópico fraco — para reforçar e re-medir até
    atingir o domínio (≥80%). Gera questões via LLM, PERSISTE-as (para a correção
    encontrá-las) e devolve uma TestSession pronta. Ao submeter via /tests/submit,
    a nova tentativa entra no mastery e a próxima abertura do plano reflete a melhora."""
    import uuid as _uuid
    cert = repo.get_certification(req.certification_id)
    if not cert:
        raise HTTPException(404, "Certificação não encontrada")
    try:
        from app.services.llm_gen import generate_questions
        questions = generate_questions(certification=cert, count=req.count,
                                       topics=[req.topic])
    except Exception as e:
        raise HTTPException(502, f"Não foi possível gerar o mini-teste: {e}")
    if not questions:
        raise HTTPException(502, "Não foi possível gerar o mini-teste. Tente novamente.")
    try:
        repo.add_questions(questions)
    except Exception as e:
        logger.warning(f"Não foi possível persistir questões do topic-quiz: {e}")
    return TestSession(
        id=str(_uuid.uuid4()), certification_id=req.certification_id,
        questions=questions, num_questions=len(questions), topics=[req.topic],
        ai_generated=True,
    )


# ── Progreso de clases del usuario ─────────────────────────────────────────────
@router.get("/me/progress")
async def my_progress(user: UserPublic = Depends(security.get_current_user)):
    return {"completed": sorted(repo.get_class_progress(user.tenant_id, user.email))}


@router.post("/me/progress/{class_id}")
async def mark_class(class_id: str, request: Request,
                     user: UserPublic = Depends(security.get_current_user)):
    repo.mark_class(user.tenant_id, user.email, class_id)
    activity.log_event(user.tenant_id, user.email, "class_complete", request=request,
                       user_name=user.name, detail={"class_id": class_id})
    return {"ok": True}


@router.delete("/me/progress/{class_id}")
async def unmark_class(class_id: str, user: UserPublic = Depends(security.get_current_user)):
    repo.unmark_class(user.tenant_id, user.email, class_id)
    return {"ok": True}


@router.get("/me/sessions/{session_id}", response_model=SessionDetail)
async def my_session_detail(session_id: str,
                            user: UserPublic = Depends(security.get_current_user)):
    owned = {a["session_id"] for a in repo.get_user_attempts(user.tenant_id, user.email)}
    if session_id not in owned:
        raise HTTPException(404, "Tentativa não encontrada")
    return SessionDetail(session_id=session_id,
                         answers=[AnswerDetail(**a) for a in repo.get_session_answers(user.tenant_id, session_id)])


# ── Admin: drill-down por usuário (escopo do tenant do admin) ─────────────────
@router.get("/admin/users/{email}/attempts", response_model=AttemptHistory)
async def admin_user_attempts(email: str, admin: UserPublic = Depends(security.require_admin)):
    return _attempts_for(admin.tenant_id, email.lower(), get_settings().PASS_MARK)


@router.get("/admin/sessions/{session_id}", response_model=SessionDetail)
async def admin_session_detail(session_id: str, admin: UserPublic = Depends(security.require_admin)):
    return SessionDetail(session_id=session_id,
                         answers=[AnswerDetail(**a) for a in repo.get_session_answers(admin.tenant_id, session_id)])


def _build_pdf(tenant_id: str, session_id: str, lang: str = "pt") -> Response:
    from app.services.pdf_report import build_attempt_pdf
    meta = repo.get_session_meta(tenant_id, session_id)
    if not meta:
        raise HTTPException(404, "Tentativa não encontrada")
    answers = repo.get_session_answers(tenant_id, session_id)
    pdf = build_attempt_pdf(meta, answers, get_settings().PASS_MARK, lang)
    fname = f"simulado_{meta.get('user_email','aluno').split('@')[0]}_{session_id[:8]}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/admin/sessions/{session_id}/pdf")
async def admin_session_pdf(session_id: str, admin: UserPublic = Depends(security.require_admin),
                            accept_language: str | None = Header(default=None)):
    return _build_pdf(admin.tenant_id, session_id, tenants_svc.resolve_lang(accept_language))


@router.get("/me/sessions/{session_id}/pdf")
async def my_session_pdf(session_id: str, user: UserPublic = Depends(security.get_current_user),
                         accept_language: str | None = Header(default=None)):
    owned = {a["session_id"] for a in repo.get_user_attempts(user.tenant_id, user.email)}
    if session_id not in owned:
        raise HTTPException(404, "Tentativa não encontrada")
    return _build_pdf(user.tenant_id, session_id, tenants_svc.resolve_lang(accept_language))


@router.get("/admin/overview", response_model=AdminOverview)
async def admin_overview(admin: UserPublic = Depends(security.require_admin)):
    s = get_settings()
    rows = repo.get_admin_overview(admin.tenant_id)
    users = [AdminUserRow(
        email=r["email"], name=r["name"], area=r.get("area"),
        status=r.get("status", "active"), is_admin=r.get("is_admin", False),
        attempts=r["attempts"], best_score=r["best_score"], last_score=r["last_score"],
        passed_any=r["passed_any"], last_attempt_at=r["last_attempt_at"],
    ) for r in rows]
    total_attempts = sum(u.attempts for u in users)
    return AdminOverview(pass_mark=s.PASS_MARK, total_users=len(users),
                         total_attempts=total_attempts, users=users)


# ── Log de acessos / atividades (auditoria do admin) ──────────────────────────
@router.get("/admin/activity", response_model=ActivityLog)
async def admin_activity(admin: UserPublic = Depends(security.require_admin),
                         email: str | None = Query(None),
                         action: str | None = Query(None),
                         limit: int = Query(200, ge=1, le=2000)):
    """Log de acessos e atividades do tenant do admin (mais recentes primeiro)."""
    summary = activity.activity_summary(admin.tenant_id)
    events = activity.get_activity(admin.tenant_id, limit=limit,
                                   email=email, action=action)
    return ActivityLog(**summary, events=[ActivityEvent(**e) for e in events])


def _csv_safe(value) -> str:
    """Neutraliza injeção de fórmula em planilhas (Excel/Sheets).
    Campos que começam com = + - @ (ou tab/CR) são prefixados com aspa simples."""
    s = "" if value is None else str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


@router.get("/admin/activity.csv")
async def admin_activity_csv(admin: UserPublic = Depends(security.require_admin),
                             email: str | None = Query(None),
                             action: str | None = Query(None),
                             limit: int = Query(2000, ge=1, le=2000)):
    """Exporta o log de atividades como CSV (para controle/auditoria offline)."""
    import csv, io, json as _json
    events = activity.get_activity(admin.tenant_id, limit=limit, email=email, action=action)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["created_at", "user_email", "user_name", "action", "detail", "ip", "user_agent"])
    for e in events:
        w.writerow([_csv_safe(e["created_at"]), _csv_safe(e["user_email"]),
                    _csv_safe(e.get("user_name") or ""), _csv_safe(e["action"]),
                    _csv_safe(_json.dumps(e.get("detail") or {}, ensure_ascii=False)),
                    _csv_safe(e.get("ip") or ""), _csv_safe(e.get("user_agent") or "")])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="activity_log.csv"'})


# ── Gestão de usuários (admin do tenant) ──────────────────────────────────────
@router.post("/admin/users")
async def admin_create_user(body: AdminCreateUser,
                            admin: UserPublic = Depends(security.require_admin)):
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(422, "E-mail inválido")
    if len(body.password) < 6:
        raise HTTPException(422, "A senha deve ter ao menos 6 caracteres")
    if not body.name.strip():
        raise HTTPException(422, "Nome obrigatório")
    if users_svc.get_user(admin.tenant_id, email):
        raise HTTPException(409, "E-mail já cadastrado neste tenant")
    users_svc.create_user(admin.tenant_id, email, body.name.strip(),
                          security.hash_password(body.password),
                          is_admin=body.is_admin, area=body.area)
    return {"ok": True}


@router.patch("/admin/users/{email}")
async def admin_update_user(email: str, body: UserProfileUpdate,
                            admin: UserPublic = Depends(security.require_admin)):
    if not users_svc.get_user(admin.tenant_id, email.lower()):
        raise HTTPException(404, "Usuário não encontrado")
    users_svc.update_profile(admin.tenant_id, email.lower(), body.name, body.area)
    return {"ok": True}


@router.patch("/admin/users/{email}/status")
async def admin_set_user_status(email: str, body: UserStatusUpdate,
                                admin: UserPublic = Depends(security.require_admin)):
    if body.status not in ("active", "suspended"):
        raise HTTPException(422, "status inválido")
    if email.lower() == admin.email.lower():
        raise HTTPException(400, "Você não pode suspender a própria conta")
    if not users_svc.get_user(admin.tenant_id, email.lower()):
        raise HTTPException(404, "Usuário não encontrado")
    users_svc.set_status(admin.tenant_id, email.lower(), body.status)
    return {"ok": True, "status": body.status}


@router.post("/admin/users/{email}/password")
async def admin_set_user_password(email: str, body: AdminPasswordSet,
                                  admin: UserPublic = Depends(security.require_admin)):
    if len(body.new_password) < 6:
        raise HTTPException(422, "A senha deve ter ao menos 6 caracteres")
    if not users_svc.get_user(admin.tenant_id, email.lower()):
        raise HTTPException(404, "Usuário não encontrado")
    users_svc.update_password(admin.tenant_id, email.lower(),
                              security.hash_password(body.new_password))
    return {"ok": True}


@router.delete("/admin/users/{email}")
async def admin_delete_user(email: str, admin: UserPublic = Depends(security.require_admin)):
    if email.lower() == admin.email.lower():
        raise HTTPException(400, "Você não pode excluir a própria conta")
    if not users_svc.get_user(admin.tenant_id, email.lower()):
        raise HTTPException(404, "Usuário não encontrado")
    users_svc.delete_user(admin.tenant_id, email.lower())
    return {"ok": True}
