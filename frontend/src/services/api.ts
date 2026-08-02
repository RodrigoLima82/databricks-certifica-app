import axios from 'axios'
import type {
  Certification, Question, Flashcard,
  TestSetupRequest, TestSession, TestSubmitRequest, TestResult,
  TokenResponse, UserPublic, AttemptHistory, AdminOverview, AuthStatus,
  SessionDetail, Theme, SignupPayload, TenantPublic, Operator, ProgramContent, LeaderboardRow,
  RoutesContent, ProgramProgress, StudyPlanResponse,
} from '@/types'

// Em Amplify (frontend) o backend roda em outro origin (App Runner): aponte
// VITE_API_BASE_URL para a URL pública do serviço (ex.: https://xxx.awsapprunner.com/api).
// Em dev/local fica '/api' (proxy do Vite) ou same-origin quando o FastAPI serve o SPA.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const api = axios.create({ baseURL: API_BASE, timeout: 120000 })

const TOKEN_KEY = 'certifica_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

// Tenant ambiente (slug): resolvido no login/landing e usado para theme + auth.
const TENANT_KEY = 'certifica_tenant'
export const getTenantSlug = () => localStorage.getItem(TENANT_KEY) || ''
export const setTenantSlug = (s: string) => localStorage.setItem(TENANT_KEY, s)
export const clearTenantSlug = () => localStorage.removeItem(TENANT_KEY)

api.interceptors.request.use(config => {
  const t = getToken()
  if (t) {
    // X-App-Auth: o gateway do Databricks Apps consome o Authorization para o
    // próprio OAuth, então o JWT do app vai num header customizado (repassado intacto).
    // Precisa casar com AUTH_HEADER no backend (default X-App-Auth).
    config.headers['X-App-Auth'] = `Bearer ${t}`
    config.headers.Authorization = `Bearer ${t}`  // Azure App Service / local
  }
  // Idioma atual (pt/es/en) → o backend responde conteúdo traduzível nesse idioma.
  const lang = localStorage.getItem('certifica_lang')
  if (lang) config.headers['Accept-Language'] = lang
  return config
})

// Auth (tenant-aware)
export const authStatus = (): Promise<AuthStatus> => api.get('/auth/status').then(r => r.data)
export const register = (tenant_slug: string, name: string, email: string, password: string): Promise<TokenResponse> =>
  api.post('/auth/register', { tenant_slug, name, email, password }).then(r => r.data)
export const login = (tenant_slug: string, email: string, password: string): Promise<TokenResponse> =>
  api.post('/auth/login', { tenant_slug, email, password }).then(r => r.data)

// Tenants
export const getTheme = (slug: string): Promise<Theme> =>
  api.get(`/tenants/${encodeURIComponent(slug)}/theme`).then(r => r.data)
export const resolveTenant = (q: string): Promise<{ slug: string }> =>
  api.get('/tenants/resolve', { params: { q } }).then(r => r.data)
export const getProgram = (slug: string): Promise<ProgramContent> =>
  api.get(`/tenants/${encodeURIComponent(slug)}/program`).then(r => r.data)
export const saveProgram = (slug: string, content: ProgramContent): Promise<ProgramContent> =>
  api.put(`/tenants/${encodeURIComponent(slug)}/program`, content).then(r => r.data)
export const getRoutes = (slug: string): Promise<RoutesContent> =>
  api.get(`/tenants/${encodeURIComponent(slug)}/routes`).then(r => r.data)
export const saveRoutes = (slug: string, content: RoutesContent): Promise<RoutesContent> =>
  api.put(`/tenants/${encodeURIComponent(slug)}/routes`, content).then(r => r.data)
export const signup = (payload: SignupPayload): Promise<TokenResponse> =>
  api.post('/tenants/signup', payload).then(r => r.data)
export const listTenants = (): Promise<TenantPublic[]> =>
  api.get('/platform/tenants').then(r => r.data)
export const createTenant = (payload: Partial<TenantPublic> & { admin_email?: string; admin_password?: string; admin_name?: string }): Promise<TenantPublic> =>
  api.post('/platform/tenants', payload).then(r => r.data)
export const setTenantStatus = (slug: string, status: 'active' | 'suspended'): Promise<TenantPublic> =>
  api.patch(`/platform/tenants/${encodeURIComponent(slug)}/status`, { status }).then(r => r.data)
export const updateTenantBranding = (slug: string, body: { name?: string; primary_color?: string; logo_url?: string }): Promise<TenantPublic> =>
  api.patch(`/platform/tenants/${encodeURIComponent(slug)}`, body).then(r => r.data)
export const listOperators = (): Promise<Operator[]> =>
  api.get('/platform/operators').then(r => r.data)
export const createOperator = (body: { name: string; email: string; password: string }): Promise<Operator> =>
  api.post('/platform/operators', body).then(r => r.data)
export const deleteOperator = (email: string): Promise<any> =>
  api.delete(`/platform/operators/${encodeURIComponent(email)}`).then(r => r.data)
export const getMe = (): Promise<UserPublic> => api.get('/auth/me').then(r => r.data)
export const changePassword = (new_password: string): Promise<TokenResponse> =>
  api.post('/auth/change-password', { new_password }).then(r => r.data)

// Tracking
export const getMyAttempts = (): Promise<AttemptHistory> =>
  api.get('/me/attempts').then(r => r.data)
export const getLeaderboard = (): Promise<LeaderboardRow[]> =>
  api.get('/leaderboard').then(r => r.data)
export const getProgress = (): Promise<{ completed: string[] }> =>
  api.get('/me/progress').then(r => r.data)
export const getProgramProgress = (): Promise<ProgramProgress> =>
  api.get('/me/program-progress').then(r => r.data)
export const markClass = (id: string): Promise<any> =>
  api.post(`/me/progress/${encodeURIComponent(id)}`).then(r => r.data)
export const unmarkClass = (id: string): Promise<any> =>
  api.delete(`/me/progress/${encodeURIComponent(id)}`).then(r => r.data)
export const getAdminOverview = (): Promise<AdminOverview> =>
  api.get('/admin/overview').then(r => r.data)
export const adminCreateUser = (body: { name: string; email: string; password: string; area?: string; is_admin?: boolean }): Promise<any> =>
  api.post('/admin/users', body).then(r => r.data)
export const adminUpdateUser = (email: string, body: { name?: string; area?: string }): Promise<any> =>
  api.patch(`/admin/users/${encodeURIComponent(email)}`, body).then(r => r.data)
export const adminSetUserStatus = (email: string, status: 'active' | 'suspended'): Promise<any> =>
  api.patch(`/admin/users/${encodeURIComponent(email)}/status`, { status }).then(r => r.data)
export const adminSetUserPassword = (email: string, new_password: string): Promise<any> =>
  api.post(`/admin/users/${encodeURIComponent(email)}/password`, { new_password }).then(r => r.data)
export const adminDeleteUser = (email: string): Promise<any> =>
  api.delete(`/admin/users/${encodeURIComponent(email)}`).then(r => r.data)
export const getAdminUserAttempts = (email: string): Promise<AttemptHistory> =>
  api.get(`/admin/users/${encodeURIComponent(email)}/attempts`).then(r => r.data)
export const getAdminActivity = (params?: { email?: string; action?: string; limit?: number }): Promise<import('@/types').ActivityLog> =>
  api.get('/admin/activity', { params }).then(r => r.data)
export const getAdminActivityCsv = (params?: { email?: string; action?: string }): Promise<Blob> =>
  api.get('/admin/activity.csv', { params, responseType: 'blob' }).then(r => r.data)
export const getAdminSession = (sessionId: string): Promise<SessionDetail> =>
  api.get(`/admin/sessions/${sessionId}`).then(r => r.data)
export const getAdminSessionPdf = (sessionId: string): Promise<Blob> =>
  api.get(`/admin/sessions/${sessionId}/pdf`, { responseType: 'blob' }).then(r => r.data)

export const getCertifications = (): Promise<Certification[]> =>
  api.get('/certifications/').then(r => r.data)

export const getCertification = (id: string): Promise<Certification> =>
  api.get(`/certifications/${id}`).then(r => r.data)

export const getCertInfo = (id: string): Promise<import('@/types').CertInfo> =>
  api.get(`/certifications/${encodeURIComponent(id)}/info`).then(r => r.data)
export const getQuestions = (id: string, topics?: string[]): Promise<Question[]> =>
  api.get(`/certifications/${id}/questions`, { params: { topics } }).then(r => r.data)

export const getFlashcards = (id: string, topics?: string[]): Promise<Flashcard[]> =>
  api.get(`/certifications/${id}/flashcards`, { params: { topics } }).then(r => r.data)

export const createTest = (req: TestSetupRequest): Promise<TestSession> =>
  api.post('/tests/', req).then(r => r.data)

// Step 4.4 — simulado completo (nº real de questões + distribuição por domínio).
// Gera dezenas de questões via LLM (mesmo em paralelo) → timeout estendido (5 min).
export const createMockExam = (certification_id: string): Promise<TestSession> =>
  api.post('/tests/mock', { certification_id }, { timeout: 300000 }).then(r => r.data)

export const submitTest = (req: TestSubmitRequest): Promise<TestResult> =>
  api.post('/tests/submit', req).then(r => r.data)

export interface Health { status: string; mode: string; llm_endpoint: string; version: string }
export const getHealth = (): Promise<Health> => api.get('/health').then(r => r.data)

// ── AI Prep Guide: loop de estudio (repair / deep-dive / hands-on) ────────────
export interface WrongAnswerIn {
  question_text: string; options: string[]; correct_answers: number[]
  selected: number[]; topic?: string; explanation?: string
}
export interface RepairItem {
  topic?: string; question_text: string; misconception: string
  why_correct: string; related_question: string
}
export interface RepairResponse { success: boolean; items: RepairItem[]; source: string; message?: string }
export const repairAnswers = (certification_id: string, wrong: WrongAnswerIn[]): Promise<RepairResponse> =>
  api.post('/generate/repair', { certification_id, wrong }).then(r => r.data)

export interface DeepDiveResponse {
  success: boolean; objective: string; core_concept: string; how_it_works: string
  when_to_use: string; common_mistakes: string; code_example: string; doc_url: string
  source: string; message?: string
}
export const deepDive = (certification_id: string, objective: string): Promise<DeepDiveResponse> =>
  api.post('/generate/deep-dive', { certification_id, objective }).then(r => r.data)

export interface HandsOnTask { task: string; objective?: string; est_minutes?: number; steps?: string[]; doc_url?: string }
export interface HandsOnResponse { success: boolean; certification_id: string; tasks: HandsOnTask[]; source: string; message?: string }
export const handsOnChecklist = (certification_id: string): Promise<HandsOnResponse> =>
  api.post(`/generate/hands-on/${encodeURIComponent(certification_id)}`).then(r => r.data)

// ── Plan de estudio adaptativo (foco nos pontos fracos + trilha) ──────────────
export const getStudyPlan = (certification_id: string): Promise<StudyPlanResponse> =>
  api.get(`/me/study-plan/${encodeURIComponent(certification_id)}`, { timeout: 120000 }).then(r => r.data)

// Mini-teste focado num tópico fraco (reforço + re-medição). Devolve uma
// TestSession pronta (questões já persistidas) → responder e chamar submitTest.
export const topicQuiz = (certification_id: string, topic: string, count = 6): Promise<TestSession> =>
  api.post('/me/topic-quiz', { certification_id, topic, count }, { timeout: 120000 }).then(r => r.data)
