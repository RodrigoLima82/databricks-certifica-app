"""
Schemas Pydantic — Certifica.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ── Autenticação / usuários ───────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    tenant_slug: str
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    tenant_slug: str
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str


class UserPublic(BaseModel):
    email: str
    name: str
    tenant_id: Optional[str] = None
    tenant_slug: Optional[str] = None
    is_admin: bool = False          # admin do próprio tenant
    is_superadmin: bool = False     # operador da plataforma (cross-tenant)
    must_change_password: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ── Tenants (multi-tenant) ────────────────────────────────────────────────────
class ThemeResponse(BaseModel):
    slug: str
    name: str
    primary_color: str = "#EC0000"
    logo_url: Optional[str] = None
    allow_self_register: bool = True
    pass_mark: int = 70


class TenantPublic(BaseModel):
    id: str
    slug: str
    name: str
    primary_color: str = "#EC0000"
    logo_url: Optional[str] = None
    pass_mark: int = 70
    allow_self_register: bool = True
    status: str = "active"
    created_at: Optional[str] = None
    user_count: int = 0
    attempt_count: int = 0


# ── Programa del tenant (página de introducción post-login) ────────────────────
class ProgramKpi(BaseModel):
    label: str = ""
    value: str = ""


class ProgramItem(BaseModel):
    title: str = ""
    desc: str = ""
    link: Optional[str] = None


class ProgramResource(BaseModel):
    label: str = ""
    url: str = ""


class ProgramContent(BaseModel):
    title: str = ""
    tagline: str = ""
    intro: str = ""
    kpis: List[ProgramKpi] = []
    pillars: List[ProgramItem] = []
    roadmap: List[ProgramItem] = []
    exam_intro: str = ""               # instrucciones del examen (datos clave)
    exam_steps: List[ProgramItem] = []  # logística paso a paso del examen proctored
    resources: List[ProgramResource] = []
    ranking_enabled: bool = False
    ranking_intro: str = ""
    ranking_tiers: List[ProgramItem] = []


# ── Rutas de aprendizaje + clases ──────────────────────────────────────────────
class ClassItem(BaseModel):
    id: str = ""                 # id estable para rastrear progreso
    title: str = ""
    desc: str = ""
    type: str = "elearning"      # elearning | lab | video | reading
    level: str = ""              # fundamentos | associate | professional
    duration: str = ""           # ej. "3h"
    free: bool = True
    url: Optional[str] = None


class RouteItem(BaseModel):
    name: str = ""
    description: str = ""
    certification_id: Optional[str] = None   # certificación objetivo (del banco global)
    classes: List[ClassItem] = []


class RoutesContent(BaseModel):
    routes: List[RouteItem] = []


class SignupRequest(BaseModel):
    company: str
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
    primary_color: str = "#EC0000"
    logo_url: Optional[str] = None
    email_domain: Optional[str] = None
    admin_name: str
    admin_email: str
    admin_password: str


class TenantStatusUpdate(BaseModel):
    status: str   # 'active' | 'suspended'


class TenantBrandingUpdate(BaseModel):
    name: Optional[str] = None
    primary_color: Optional[str] = None
    logo_url: Optional[str] = None   # URL o data URI (ej. SVG en base64)


class TenantCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
    name: str
    primary_color: str = "#EC0000"
    logo_url: Optional[str] = None
    pass_mark: int = 70
    allow_self_register: bool = True
    admin_email: Optional[str] = None
    admin_name: Optional[str] = None
    admin_password: Optional[str] = None
    email_domain: Optional[str] = None


# ── Certificações ─────────────────────────────────────────────────────────────
class Resource(BaseModel):
    label: str
    url: str


class CertDomain(BaseModel):
    name: str
    weight: Optional[int] = None


class CertInfo(BaseModel):
    questions: str = ""
    duration: str = ""
    format: str = ""
    language: str = ""
    validity: str = ""
    experience: str = ""
    exam_guide_url: Optional[str] = None
    domains: List[CertDomain] = []


class Certification(BaseModel):
    id: str
    name: str
    type: str
    level: str
    description: str
    exam_guide_url: Optional[str] = None
    topics: List[str] = []
    resources: List[Resource] = []


# ── Questões ──────────────────────────────────────────────────────────────────
QuestionType = Literal["multiple_choice", "multiple_select", "true_false"]


class Question(BaseModel):
    id: str
    certification_id: str
    topic: str
    question_text: str
    question_type: QuestionType = "multiple_choice"
    options: List[str]
    correct_answers: List[int]
    explanation: str = ""
    difficulty: int = 3
    is_ai_generated: bool = False


class Flashcard(BaseModel):
    id: str
    certification_id: str
    topic: str
    front: str
    back: str
    difficulty: int = 2


# ── Simulado (test session) ─────────────────────────────────────────────────
class TestSetupRequest(BaseModel):
    certification_id: str
    num_questions: int = Field(default=20, ge=5, le=60)
    topics: Optional[List[str]] = None      # None = todos os tópicos
    ai_generate: bool = False               # gerar questões novas via LLM
    ai_count: int = Field(default=5, ge=0, le=10)


class DomainAllocation(BaseModel):
    domain: str
    requested: int
    generated: int


class TestSession(BaseModel):
    id: str
    certification_id: str
    questions: List[Question]
    num_questions: int
    topics: List[str]
    ai_generated: bool
    is_mock: bool = False                         # Step 4.4: simulado completo
    distribution: List[DomainAllocation] = []     # distribuição por domínio (só mock)


class MockExamRequest(BaseModel):
    certification_id: str


class AnswerSubmission(BaseModel):
    question_id: str
    selected: List[int]
    time_spent_sec: Optional[float] = None


class TestSubmitRequest(BaseModel):
    session_id: str
    certification_id: str
    answers: List[AnswerSubmission]
    duration_sec: Optional[float] = None


class AnswerResult(BaseModel):
    question_id: str
    topic: str
    selected: List[int]
    correct_answers: List[int]
    is_correct: bool


class TopicScore(BaseModel):
    topic: str
    correct: int
    total: int


class TestResult(BaseModel):
    session_id: str
    certification_id: str
    score_pct: float
    correct: int
    total: int
    answered: int
    passed: bool = False
    pass_mark: int = 70
    repeated_questions: int = 0
    duration_sec: Optional[float] = None
    by_topic: List[TopicScore]
    results: List[AnswerResult]


# ── Plano de estudo adaptativo (foco nos pontos fracos) ──────────────────────
class StudyPlanClass(BaseModel):
    """Aula da trilha recomendada para um tópico fraco."""
    id: str = ""
    title: str = ""
    type: str = "elearning"
    duration: str = ""
    url: Optional[str] = None
    route_name: str = ""


class StudyPlanTopic(BaseModel):
    topic: str
    correct: int
    total: int
    pct: float
    recent_pct: float
    first_pct: float
    attempts: int
    status: str                       # weak | improving | mastered
    trend: str                        # up | down | flat
    classes: List[StudyPlanClass] = []   # aulas da trilha que cobrem o tópico


class StudyPlanResponse(BaseModel):
    success: bool = True
    certification_id: str
    mastery_mark: int = 80            # % para considerar o tópico dominado
    pass_mark: int = 70
    attempts_count: int = 0           # nº de provas feitas nesta cert
    topics: List[StudyPlanTopic] = []
    source: str = "llm"               # llm | mock | none
    message: Optional[str] = None


class TopicQuizRequest(BaseModel):
    certification_id: str
    topic: str
    count: int = Field(default=6, ge=1, le=10)


# ── Geração via LLM ───────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    certification_id: str
    count: int = Field(default=5, ge=1, le=10)
    topics: Optional[List[str]] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    persist: bool = False                   # gravar no RDS


class GenerateResponse(BaseModel):
    success: bool
    questions: List[Question] = []
    source: str = "llm"                     # llm | mock | error
    message: Optional[str] = None


# ── AI Prep Guide: loop de estudo (repair / deep-dive / hands-on) ─────────────
class WrongAnswerIn(BaseModel):
    question_text: str
    options: List[str] = []
    correct_answers: List[int] = []
    selected: List[int] = []
    topic: Optional[str] = None
    explanation: Optional[str] = None


class RepairRequest(BaseModel):
    certification_id: str
    wrong: List[WrongAnswerIn]


class RepairItem(BaseModel):
    topic: Optional[str] = None
    question_text: str = ""
    misconception: str = ""
    why_correct: str = ""
    related_question: str = ""


class RepairResponse(BaseModel):
    success: bool
    items: List[RepairItem] = []
    source: str = "llm"
    message: Optional[str] = None


class DeepDiveRequest(BaseModel):
    certification_id: str
    objective: str


class DeepDiveResponse(BaseModel):
    success: bool
    objective: str = ""
    core_concept: str = ""
    how_it_works: str = ""
    when_to_use: str = ""
    common_mistakes: str = ""
    code_example: str = ""
    doc_url: str = ""
    source: str = "llm"
    message: Optional[str] = None


class HandsOnTask(BaseModel):
    task: str
    objective: Optional[str] = None
    est_minutes: Optional[int] = None
    steps: List[str] = []                 # passo-a-passo curto de como fazer
    doc_url: Optional[str] = None         # link oficial docs.databricks.com (grounding)


class HandsOnResponse(BaseModel):
    success: bool
    certification_id: str
    tasks: List[HandsOnTask] = []
    source: str = "llm"
    message: Optional[str] = None


# ── Rastreamento / histórico ─────────────────────────────────────────────────
class Attempt(BaseModel):
    session_id: str
    certification_id: str
    certification_name: Optional[str] = None
    score_pct: float
    correct: int
    total: int
    passed: bool
    ai_generated: bool = False
    repeated_questions: int = 0             # nº de questões já vistas em tentativas anteriores
    created_at: Optional[str] = None


class AttemptHistory(BaseModel):
    user_email: str
    pass_mark: int
    attempts: List[Attempt]


class AdminUserRow(BaseModel):
    email: str
    name: str
    area: Optional[str] = None
    status: str = "active"
    is_admin: bool = False
    attempts: int = 0
    best_score: Optional[float] = None
    last_score: Optional[float] = None
    passed_any: bool = False
    last_attempt_at: Optional[str] = None


class AdminOverview(BaseModel):
    pass_mark: int
    total_users: int
    total_attempts: int
    users: List[AdminUserRow]


# ── Log de acessos / atividades (auditoria do admin) ──────────────────────────
class ActivityEvent(BaseModel):
    id: str
    user_email: str
    user_name: Optional[str] = None
    action: str
    detail: dict = {}
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[str] = None


class ActivityLog(BaseModel):
    total_events: int = 0
    logins_7d: int = 0
    active_users_7d: int = 0
    events: List[ActivityEvent] = []


class ProgramProgress(BaseModel):
    percent: int = 0
    classes_done: int = 0
    classes_total: int = 0
    certs_passed: int = 0
    certs_total: int = 0


class LeaderboardRow(BaseModel):
    rank: int = 0
    email: str
    name: str
    area: Optional[str] = None
    points: float = 0
    passed: int = 0
    attempts: int = 0
    classes: int = 0


# ── Gestão de usuários (admin do tenant) ──────────────────────────────────────
class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    area: Optional[str] = None


class UserStatusUpdate(BaseModel):
    status: str   # 'active' | 'suspended'


class AdminPasswordSet(BaseModel):
    new_password: str


class AdminCreateUser(BaseModel):
    name: str
    email: str
    password: str
    area: Optional[str] = None
    is_admin: bool = False


class OperatorCreate(BaseModel):
    name: str
    email: str
    password: str


class Operator(BaseModel):
    email: str
    name: str
    created_at: Optional[str] = None


class AnswerDetail(BaseModel):
    question_id: str
    topic: str
    question_text: str
    options: List[str]
    correct_answers: List[int]
    selected: List[int]
    is_correct: bool
    explanation: str = ""
    is_ai_generated: bool = False


class SessionDetail(BaseModel):
    session_id: str
    answers: List[AnswerDetail]
