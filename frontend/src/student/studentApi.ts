import { apiMutate, apiRequest } from '../api/campusPulseApi'

export interface StudentRecord {
  id: number
  student_code: string
  full_name: string
  program: string
  department: string
  year_of_study: number
  cohort: string
  advisor_name: string | null
  mentor_name: string | null
}

export interface StudentMe {
  user_id: number
  email: string
  full_name: string
  student: StudentRecord
  profile_completion: number
}

export interface LinkStatus {
  linked: boolean
  is_student: boolean
  student: Pick<
    StudentRecord,
    | 'id'
    | 'student_code'
    | 'full_name'
    | 'program'
    | 'department'
    | 'year_of_study'
    | 'cohort'
  > | null
}

export interface NotificationItem {
  id: number
  category: string
  title: string
  body: string
  is_read: boolean
  assignment_id: number | null
  created_at: string
}

export interface SupportRequestSummary {
  id: number
  request_type: string
  subject: string
  status: string
  created_at: string
}

export interface AchievementSummary {
  code: string
  title: string
  earned_at: string
}

export interface HomeSummary {
  student: StudentRecord
  term: string
  attendance_percentage: number | null
  academic_average: number | null
  pending_assignments: number
  due_soon_count: number
  completed_assignments: number
  pulse_balance: number
  lifetime_earned: number
  affordable_rewards: number
  upcoming_deadlines: Array<{
    assignment_id: number
    title: string
    subject: string
    due_at: string
  }>
  recent_feedback: Array<{
    submission_id: number
    assignment_id: number
    assignment_title: string | null
    marks_obtained: number | null
    max_marks: number | null
    feedback: string | null
    graded_at: string | null
  }>
  achievements: AchievementSummary[]
  notifications: NotificationItem[]
  unread_notifications: number
  support_requests: SupportRequestSummary[]
}

export interface PortalProfile {
  contact_email: string | null
  contact_phone: string | null
  bio: string | null
  skills: string | null
  certifications: string | null
}

export interface ProfileData {
  student: StudentRecord
  profile: PortalProfile
  enrolled_courses: string[]
  profile_completion: number
}

export interface SignalEntry {
  signal_name: string
  numeric_value: number | null
  text_value: string | null
  recorded_at: string
  source_label: string | null
  quality_status: string
}

export interface AcademicsData {
  student: StudentRecord
  domains: Record<string, SignalEntry[]>
  assignment_grades: Array<{
    assignment_id: number
    title: string
    subject: string
    marks_obtained: number | null
    max_marks: number
    quality_points: number | null
    timing_points: number | null
    feedback: string | null
    is_late: boolean
    graded_at: string | null
  }>
  latest_attendance: number | null
  latest_average: number | null
  note: string
}

export type SubmissionState =
  | 'not_submitted'
  | 'draft'
  | 'submitted'
  | 'submitted_late'
  | 'graded'
  | 'returned'
  | 'closed'

export interface SubmissionInfo {
  id: number
  text_answer: string | null
  link_url: string | null
  status: string
  is_late: boolean
  submitted_at: string
  resubmission_count: number
  marks_obtained: number | null
  timing_points: number | null
  quality_points: number | null
  feedback: string | null
  feedback_released: boolean
  graded_at: string | null
}

export interface AssignmentListItem {
  id: number
  title: string
  description: string
  instructions: string | null
  subject: string
  teacher_name: string | null
  status: string
  published_at: string | null
  due_at: string
  max_marks: number
  accepted_submission_types: string
  allow_late_submissions: boolean
  submission_state: SubmissionState
  submission: SubmissionInfo | null
}

export interface AssignmentDetail {
  id: number
  title: string
  description: string
  instructions: string | null
  subject: string
  max_marks: number
  allow_late_submissions: boolean
  late_window_hours: number
  status: string
  teacher_name: string | null
  cohort: string
  published_at: string | null
  due_at: string
  accepted_submission_types: string
  submission: SubmissionInfo | null
}

export interface PulseBalance {
  balance: number
  lifetime_earned: number
  lifetime_redeemed: number
  pending_quality_reviews: number
}

export interface LedgerEntry {
  id: number
  txn_type: string
  amount: number
  reason: string
  assignment_id: number | null
  assignment_title: string | null
  timing_points: number | null
  quality_points: number | null
  created_at: string
}

export interface LeaderboardEntry {
  rank: number
  student_id: number
  display_name: string
  cohort: string
  net_earned: number
  is_current_student: boolean
}

export interface LeaderboardData {
  page: number
  page_size: number
  total: number
  cohort_filter: string | null
  entries: LeaderboardEntry[]
  me: { rank: number | null; net_earned: number }
  metric_note: string
}

export interface RewardItem {
  id: number
  sku: string
  name: string
  description: string
  reward_type: string
  cost: number
  stock: number | null
  affordable: boolean
  points_needed: number
  already_redeemed: boolean
}

export interface RewardsData {
  balance: number
  rewards: RewardItem[]
}

export interface RedeemResult {
  reference: string
  reward: { id: number; name: string; cost: number; reward_type: string }
  balance_after: number
  message: string
}

export interface RedemptionRecord {
  id: number
  reference: string
  reward_name: string | null
  reward_type: string | null
  cost: number
  status: string
  created_at: string
}

export interface NotificationsData {
  unread: number
  notifications: NotificationItem[]
}

export interface AchievementItem {
  code: string
  title: string
  description: string
  earned_at: string
}

export interface SupportRequestRecord {
  id: number
  request_type: string
  subject: string
  details: string
  status: string
  response: string | null
  created_at: string
  updated_at: string
}

export interface EnrollResult {
  linked: boolean
  student: StudentRecord
  message: string
}

export const studentApi = {
  linkStatus: () => apiRequest<LinkStatus>('/api/student/link-status'),

  enroll: (studentCode: string, enrollmentCode: string) =>
    apiMutate<EnrollResult>('/api/student/enroll', 'POST', {
      student_code: studentCode,
      enrollment_code: enrollmentCode,
    }),

  me: () => apiRequest<StudentMe>('/api/student/me'),

  home: () => apiRequest<HomeSummary>('/api/student/home'),

  profile: () => apiRequest<ProfileData>('/api/student/profile'),

  updateProfile: (payload: Partial<PortalProfile>) =>
    apiMutate<{
      profile: PortalProfile
      profile_completion: number
      message: string
    }>('/api/student/profile', 'PATCH', payload),

  academics: () => apiRequest<AcademicsData>('/api/student/academics'),

  assignments: (filter: string) =>
    apiRequest<AssignmentListItem[]>(
      `/api/student/assignments?filter=${encodeURIComponent(filter)}`,
    ),

  assignment: (assignmentId: number) =>
    apiRequest<AssignmentDetail>(`/api/student/assignments/${assignmentId}`),

  submitAssignment: (
    assignmentId: number,
    textAnswer: string,
    linkUrl: string | null,
    asDraft: boolean,
  ) =>
    apiMutate<{ submission: SubmissionInfo; message: string }>(
      `/api/student/assignments/${assignmentId}/submit`,
      'POST',
      { text_answer: textAnswer, link_url: linkUrl, as_draft: asDraft },
    ),

  pulseBalance: () => apiRequest<PulseBalance>('/api/student/pulse/balance'),

  ledger: (type: string) =>
    apiRequest<LedgerEntry[]>(
      `/api/student/pulse/ledger?type=${encodeURIComponent(type)}`,
    ),

  leaderboard: (cohort: string | null, page: number, pageSize = 10) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (cohort) params.set('cohort', cohort)
    return apiRequest<LeaderboardData>(
      `/api/student/marketplace/leaderboard?${params.toString()}`,
    )
  },

  rewards: () => apiRequest<RewardsData>('/api/student/marketplace/rewards'),

  redeem: (rewardId: number) =>
    apiMutate<RedeemResult>('/api/student/marketplace/redeem', 'POST', {
      reward_id: rewardId,
    }),

  redemptions: () =>
    apiRequest<RedemptionRecord[]>('/api/student/marketplace/redemptions'),

  notifications: () =>
    apiRequest<NotificationsData>('/api/student/notifications'),

  markNotificationRead: (notificationId: number) =>
    apiMutate<{ id: number; is_read: boolean }>(
      `/api/student/notifications/${notificationId}/read`,
      'POST',
      {},
    ),

  markAllNotificationsRead: () =>
    apiMutate<{ updated: number; message: string }>(
      '/api/student/notifications/read-all',
      'POST',
      {},
    ),

  achievements: () => apiRequest<AchievementItem[]>('/api/student/achievements'),

  supportRequests: () =>
    apiRequest<SupportRequestRecord[]>('/api/student/support-requests'),

  createSupportRequest: (
    requestType: string,
    subject: string,
    details: string,
  ) =>
    apiMutate<{ id: number; status: string; message: string }>(
      '/api/student/support-requests',
      'POST',
      { request_type: requestType, subject, details },
    ),
}
