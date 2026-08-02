export interface Resource {
  label: string
  url: string
}

export interface Certification {
  id: string
  name: string
  type: string
  level: 'associate' | 'professional' | string
  description: string
  exam_guide_url?: string
  topics: string[]
  resources: Resource[]
}

export type QuestionType = 'multiple_choice' | 'multiple_select' | 'true_false'

export interface Question {
  id: string
  certification_id: string
  topic: string
  question_text: string
  question_type: QuestionType
  options: string[]
  correct_answers: number[]
  explanation: string
  difficulty: number
  is_ai_generated: boolean
}

export interface Flashcard {
  id: string
  certification_id: string
  topic: string
  front: string
  back: string
  difficulty: number
}

export interface TestSetupRequest {
  certification_id: string
  num_questions: number
  topics?: string[]
  ai_generate: boolean
  ai_count: number
}

export interface DomainAllocation {
  domain: string
  requested: number
  generated: number
}

export interface TestSession {
  id: string
  certification_id: string
  questions: Question[]
  num_questions: number
  topics: string[]
  ai_generated: boolean
  is_mock?: boolean
  distribution?: DomainAllocation[]
}

export interface AnswerSubmission {
  question_id: string
  selected: number[]
  time_spent_sec?: number
}

// Plan de estudio adaptativo
export interface StudyPlanClass {
  id: string
  title: string
  type: string
  duration: string
  url?: string
  route_name: string
}

export interface StudyPlanTopic {
  topic: string
  correct: number
  total: number
  pct: number
  recent_pct: number
  first_pct: number
  attempts: number
  status: 'weak' | 'improving' | 'mastered'
  trend: 'up' | 'down' | 'flat'
  classes: StudyPlanClass[]
}

export interface StudyPlanResponse {
  success: boolean
  certification_id: string
  mastery_mark: number
  pass_mark: number
  attempts_count: number
  topics: StudyPlanTopic[]
  source: string
  message?: string
}

export interface TestSubmitRequest {
  session_id: string
  certification_id: string
  answers: AnswerSubmission[]
  duration_sec?: number
}

export interface AnswerResult {
  question_id: string
  topic: string
  selected: number[]
  correct_answers: number[]
  is_correct: boolean
}

export interface TopicScore { topic: string; correct: number; total: number }

export interface TestResult {
  session_id: string
  certification_id: string
  score_pct: number
  correct: number
  total: number
  answered: number
  passed: boolean
  pass_mark: number
  repeated_questions: number
  duration_sec?: number
  by_topic: TopicScore[]
  results: AnswerResult[]
}

// ── Auth / tenant / tracking ──────────────────────────────────────────────────
export interface UserPublic {
  email: string
  name: string
  tenant_id?: string
  tenant_slug?: string
  is_admin: boolean
  is_superadmin?: boolean
  must_change_password: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserPublic
}

export interface AuthStatus {
  auth_enabled: boolean
  pass_mark: number
}

export interface Theme {
  slug: string
  name: string
  primary_color: string
  logo_url?: string
  allow_self_register: boolean
  pass_mark: number
}

export interface SignupPayload {
  company: string
  slug: string
  primary_color: string
  logo_url?: string
  email_domain?: string
  admin_name: string
  admin_email: string
  admin_password: string
}

export interface Operator {
  email: string
  name: string
  created_at?: string
}

export interface LeaderboardRow {
  rank: number
  email: string
  name: string
  area?: string
  points: number
  passed: number
  attempts: number
  classes: number
}

export interface ProgramProgress {
  percent: number
  classes_done: number
  classes_total: number
  certs_passed: number
  certs_total: number
}

export interface CertDomain { name: string; weight?: number | null }
export interface CertInfo {
  questions: string; duration: string; format: string; language: string
  validity: string; experience: string; exam_guide_url?: string; domains: CertDomain[]
}

export interface ClassItem { id: string; title: string; desc: string; type: string; level?: string; duration: string; free?: boolean; url?: string | null }
export interface RouteItem { name: string; description: string; certification_id?: string | null; classes: ClassItem[] }
export interface RoutesContent { routes: RouteItem[] }

export interface ProgramItem { title: string; desc: string; link?: string | null }
export interface ProgramKpi { label: string; value: string }
export interface ProgramResource { label: string; url: string }
export interface ProgramContent {
  title: string
  tagline: string
  intro: string
  kpis: ProgramKpi[]
  pillars: ProgramItem[]
  roadmap: ProgramItem[]
  exam_intro: string
  exam_steps: ProgramItem[]
  resources: ProgramResource[]
  ranking_enabled: boolean
  ranking_intro: string
  ranking_tiers: ProgramItem[]
}

export interface TenantPublic {
  id: string
  slug: string
  name: string
  primary_color: string
  logo_url?: string
  pass_mark: number
  allow_self_register: boolean
  status: string
  created_at?: string
  user_count: number
  attempt_count: number
}

export interface Attempt {
  session_id: string
  certification_id: string
  certification_name?: string
  score_pct: number
  correct: number
  total: number
  passed: boolean
  ai_generated: boolean
  repeated_questions: number
  created_at?: string
}

export interface AttemptHistory {
  user_email: string
  pass_mark: number
  attempts: Attempt[]
}

export interface AdminUserRow {
  email: string
  name: string
  area?: string
  status: string
  is_admin: boolean
  attempts: number
  best_score?: number
  last_score?: number
  passed_any: boolean
  last_attempt_at?: string
}

export interface AdminOverview {
  pass_mark: number
  total_users: number
  total_attempts: number
  users: AdminUserRow[]
}

export interface ActivityEvent {
  id: string
  user_email: string
  user_name?: string | null
  action: string
  detail: Record<string, any>
  ip?: string | null
  user_agent?: string | null
  created_at?: string | null
}

export interface ActivityLog {
  total_events: number
  logins_7d: number
  active_users_7d: number
  events: ActivityEvent[]
}

export interface AnswerDetail {
  question_id: string
  topic: string
  question_text: string
  options: string[]
  correct_answers: number[]
  selected: number[]
  is_correct: boolean
  explanation: string
  is_ai_generated: boolean
}

export interface SessionDetail {
  session_id: string
  answers: AnswerDetail[]
}
