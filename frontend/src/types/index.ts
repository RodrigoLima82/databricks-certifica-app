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

export interface TestSession {
  id: string
  certification_id: string
  questions: Question[]
  num_questions: number
  topics: string[]
  ai_generated: boolean
}

export interface AnswerSubmission {
  question_id: string
  selected: number[]
  time_spent_sec?: number
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

// ── Auth / tracking ──────────────────────────────────────────────────────────
export interface UserPublic {
  email: string
  name: string
  is_admin: boolean
  must_change_password: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserPublic
}

export interface AuthStatus {
  auth_enabled: boolean
  allow_self_register: boolean
  pass_mark: number
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
