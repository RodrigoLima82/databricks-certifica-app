"""
Schemas Pydantic — Databricks Certifica.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ── Autenticação / usuários ───────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str


class UserPublic(BaseModel):
    email: str
    name: str
    is_admin: bool = False
    must_change_password: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ── Certificações ─────────────────────────────────────────────────────────────
class Resource(BaseModel):
    label: str
    url: str


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


class TestSession(BaseModel):
    id: str
    certification_id: str
    questions: List[Question]
    num_questions: int
    topics: List[str]
    ai_generated: bool


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


# ── Geração via LLM ───────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    certification_id: str
    count: int = Field(default=5, ge=1, le=10)
    topics: Optional[List[str]] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    persist: bool = False                   # gravar no Lakebase


class GenerateResponse(BaseModel):
    success: bool
    questions: List[Question] = []
    source: str = "llm"                     # llm | mock | error
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
    attempts: int
    best_score: Optional[float] = None
    last_score: Optional[float] = None
    passed_any: bool = False
    last_attempt_at: Optional[str] = None


class AdminOverview(BaseModel):
    pass_mark: int
    total_users: int
    total_attempts: int
    users: List[AdminUserRow]


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
