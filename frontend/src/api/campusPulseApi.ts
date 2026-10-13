
export type DemoRole =
  | 'student'
  | 'faculty'
  | 'mentor'
  | 'hod'
  | 'counsellor'
  | 'finance'
  | 'placement'

export interface Student {
  id: number
  student_code: string
  full_name: string
  program: string
  department: string
  year_of_study: number
  cohort: string
  advisor_name: string | null
  mentor_name: string | null
  created_at: string
}

export interface CohortAnalytics {
  cohort: string | null
  generated_at: string
  stale_after_days: number
  student_count: number
  assessment_coverage: {
    assessed_students: number
    students_without_assessment: number
  }
  risk_distribution: Record<string, number>
  intervention_workload: {
    total: number
    by_status: Record<string, number>
    overdue_open_interventions: number
  }
  outcome_coverage: {
    recorded_outcomes: number
    interventions_with_outcomes: number
    by_evidence_quality: Record<string, number>
  }
  data_quality: {
    signals_examined: number
    missing_signals: number
    stale_signals: number
    note: string
  }
  interpretation_note: string
}

export interface Recommendation {
  id: number
  student_id: number
  student_name: string
  student_code: string
  assessment_id: number | null
  intervention_type: string
  rationale: string
  contributing_signals: unknown[] | Record<string, unknown>
  intended_role: string
  suggested_next_step: string
  priority: string
  status: string
  decision_reason: string | null
  created_at: string
  updated_at: string
}

export interface Intervention {
  id: number
  student_id: number
  student_name: string
  student_code: string
  recommendation_id: number | null
  intervention_type: string
  description: string
  assigned_role: string
  assigned_owner: string
  supporting_role: string | null
  due_date: string
  status: string
  priority: string
  override_reason: string | null
  created_at: string
  updated_at: string
}

// Authenticated session state. The signed access token returned by the
// backend is persisted in localStorage under the session key below.
// Note: localStorage is a convenience store, not a security boundary; an
// XSS vulnerability in the page could read the token. The backend enforces
// authorization regardless of what client state claims.
const SESSION_KEY = 'campuspulse_demo_session'

export interface AuthUser {
  id: number
  email: string
  full_name: string
  role: DemoRole
}

interface StoredSession {
  token: string
  user: AuthUser
}

function readStoredSession(): StoredSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as StoredSession
    return parsed?.token ? parsed : null
  } catch {
    return null
  }
}

let currentSession: StoredSession | null = readStoredSession()

let onUnauthorized: (() => void) | null = null

/** Register a callback invoked when the backend rejects the session (401). */
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

/** The signed-in account, or null when signed out. */
export function getAuthUser(): AuthUser | null {
  return currentSession?.user ?? null
}

function storeSession(session: StoredSession) {
  currentSession = session
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

function clearSession() {
  currentSession = null
  localStorage.removeItem(SESSION_KEY)
}

/** Sign out locally; the backend token simply expires on its own. */
export function logout() {
  clearSession()
}

function authHeaders(): Record<string, string> {
  return currentSession?.token
    ? { Authorization: `Bearer ${currentSession.token}` }
    : {}
}

function handleUnauthorized(message: string): never {
  clearSession()
  onUnauthorized?.()
  throw new Error(message)
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: {
      ...authHeaders(),
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    let message = `Request failed (${response.status})`

    try {
      const body = await response.json()
      message = body.detail ?? message
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }

    if (response.status === 401) handleUnauthorized(message)
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

async function mutate<T>(
  path: string,
  method: 'POST' | 'PATCH',
  body: Record<string, unknown>,
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: {
      ...authHeaders(),
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let message = `Request failed (${response.status})`

    try {
      const result = await response.json()
      message = result.detail ?? message
    } catch {
      // Retain the HTTP status message.
    }

    if (response.status === 401) handleUnauthorized(message)
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

// Shared request helpers. The student portal reuses the same session
// handling (bearer token, 401 sign-out) as the staff workspace.
export async function apiRequest<T>(path: string): Promise<T> {
  return request<T>(path)
}

export async function apiMutate<T>(
  path: string,
  method: 'POST' | 'PATCH',
  body: Record<string, unknown>,
): Promise<T> {
  return mutate<T>(path, method, body)
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: { id: number; email: string; full_name: string; role: DemoRole }
  message: string
}

export async function registerWithDatabase(fullName: string, email: string, password: string, role: DemoRole): Promise<LoginResponse> {
  const response = await fetch('/api/auth/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ full_name: fullName, email, password, role }),
  })
  const result = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(result.detail ?? `Registration failed (${response.status})`)
  const login = result as LoginResponse
  storeSession({ token: login.access_token, user: login.user })
  return login
}

export async function loginWithDatabase(email: string, password: string, role: DemoRole): Promise<LoginResponse> {
  const response = await fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ email, password, role }),
  })
  const result = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(result.detail ?? `Sign in failed (${response.status})`)
  const login = result as LoginResponse
  storeSession({ token: login.access_token, user: login.user })
  return login
}

export const campusPulseApi = {
  getStudents: () => request<Student[]>('/api/students'),

  getStudent: (studentId: number) =>
    request<Student>(`/api/students/${studentId}`),

  getStudent360: (studentId: number) =>
    request<{
      student: Student
      consents: Array<{
        purpose: string
        status: string
        recorded_at: string
      }>
      signals: Array<{
        id: number
        domain: string
        signal_name: string
        numeric_value: number | null
        text_value: string | null
        recorded_at: string
        source_label: string | null
        quality_status: string
        purpose_category: string | null
      }>
      viewer_role: DemoRole
    }>(`/api/students/${studentId}/360`),

  getCohortAnalytics: (cohort?: string) => {
    const query = cohort
      ? `?cohort=${encodeURIComponent(cohort)}`
      : ''

    return request<CohortAnalytics>(`/api/analytics/cohort${query}`)
  },

  getRecommendations: () =>
    request<Recommendation[]>('/api/recommendations'),

  getInterventions: () =>
    request<Intervention[]>('/api/interventions'),

  reviewRecommendation: (
    id: number,
    decision: 'approved' | 'declined',
    reason?: string,
  ) =>
    mutate<{ id: number; status: string; message: string }>(
      `/api/recommendations/${id}/review`,
      'POST',
      { decision, reason },
    ),

  updateInterventionStatus: (
    id: number,
    status: string,
    reason?: string,
  ) =>
    mutate<{
      intervention_id: number
      status: string
      message: string
    }>(
      `/api/interventions/${id}/status`,
      'PATCH',
      { status, reason },
    ),

  recordFollowUp: (id: number, note: string) =>
    mutate<{
      intervention_id: number
      status: string
      message: string
    }>(
      `/api/interventions/${id}/follow-up`,
      'POST',
      { note },
    ),
      createIntervention: (
    recommendationId: number,
    payload: {
      assigned_role: DemoRole
      assigned_owner: string
      due_date: string
      supporting_role?: DemoRole | null
      priority: 'low' | 'medium' | 'high' | 'urgent'
    },
  ) =>
    mutate<{
      id: number
      student_id: number
      recommendation_id: number
      status: string
      message: string
    }>(
      `/api/recommendations/${recommendationId}/interventions`,
      'POST',
      payload,
    ),

  recordOutcome: (
    interventionId: number,
    payload: {
      metric_name: string
      baseline_value?: number | null
      baseline_date?: string | null
      follow_up_value?: number | null
      follow_up_date?: string | null
      classification: 'improved' | 'unchanged' | 'declined' | 'mixed' | 'insufficient_evidence'
      outcome_note?: string | null
      evidence_quality: 'high' | 'medium' | 'low' | 'unknown'
    },
  ) =>
    mutate<{
      outcome_id: number
      intervention_id: number
      classification: string
      message: string
    }>(
      `/api/interventions/${interventionId}/outcomes`,
      'POST',
      payload,
    ),

  runAcademicAssessment: (studentId: number) =>
    mutate<Record<string, unknown>>(
      `/api/students/${studentId}/assessments/academic-support`,
      'POST',
      {},
    ),
}
