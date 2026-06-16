import axios from 'axios'
import type {
  Certification, Question, Flashcard,
  TestSetupRequest, TestSession, TestSubmitRequest, TestResult,
  TokenResponse, UserPublic, AttemptHistory, AdminOverview, AuthStatus,
  SessionDetail,
} from '@/types'

const api = axios.create({ baseURL: '/api', timeout: 120000 })

const TOKEN_KEY = 'dbxcert_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

api.interceptors.request.use(config => {
  const t = getToken()
  if (t) {
    // X-App-Auth: o gateway do Databricks Apps consome o Authorization para o
    // próprio OAuth, então o JWT do app vai num header customizado (repassado intacto).
    config.headers['X-App-Auth'] = `Bearer ${t}`
    config.headers.Authorization = `Bearer ${t}`  // Azure App Service / local
  }
  return config
})

// Auth
export const authStatus = (): Promise<AuthStatus> => api.get('/auth/status').then(r => r.data)
export const register = (name: string, email: string, password: string): Promise<TokenResponse> =>
  api.post('/auth/register', { name, email, password }).then(r => r.data)
export const login = (email: string, password: string): Promise<TokenResponse> =>
  api.post('/auth/login', { email, password }).then(r => r.data)
export const getMe = (): Promise<UserPublic> => api.get('/auth/me').then(r => r.data)
export const changePassword = (new_password: string): Promise<TokenResponse> =>
  api.post('/auth/change-password', { new_password }).then(r => r.data)

// Tracking
export const getMyAttempts = (): Promise<AttemptHistory> =>
  api.get('/me/attempts').then(r => r.data)
export const getAdminOverview = (): Promise<AdminOverview> =>
  api.get('/admin/overview').then(r => r.data)
export const getAdminUserAttempts = (email: string): Promise<AttemptHistory> =>
  api.get(`/admin/users/${encodeURIComponent(email)}/attempts`).then(r => r.data)
export const getAdminSession = (sessionId: string): Promise<SessionDetail> =>
  api.get(`/admin/sessions/${sessionId}`).then(r => r.data)
export const getAdminSessionPdf = (sessionId: string): Promise<Blob> =>
  api.get(`/admin/sessions/${sessionId}/pdf`, { responseType: 'blob' }).then(r => r.data)

export const getCertifications = (): Promise<Certification[]> =>
  api.get('/certifications/').then(r => r.data)

export const getCertification = (id: string): Promise<Certification> =>
  api.get(`/certifications/${id}`).then(r => r.data)

export const getQuestions = (id: string, topics?: string[]): Promise<Question[]> =>
  api.get(`/certifications/${id}/questions`, { params: { topics } }).then(r => r.data)

export const getFlashcards = (id: string, topics?: string[]): Promise<Flashcard[]> =>
  api.get(`/certifications/${id}/flashcards`, { params: { topics } }).then(r => r.data)

export const createTest = (req: TestSetupRequest): Promise<TestSession> =>
  api.post('/tests/', req).then(r => r.data)

export const submitTest = (req: TestSubmitRequest): Promise<TestResult> =>
  api.post('/tests/submit', req).then(r => r.data)

export interface Health { status: string; mode: string; llm_endpoint: string; version: string }
export const getHealth = (): Promise<Health> => api.get('/health').then(r => r.data)
