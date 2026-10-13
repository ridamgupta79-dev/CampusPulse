import { useCallback, useEffect, useState } from 'react'
import { Award, CalendarClock, ClipboardList, Trophy, Zap } from 'lucide-react'
import {
  studentApi,
  type HomeSummary,
} from '../studentApi'
import {
  SUPPORT_TYPE_LABELS,
  dueLabel,
  formatUtcDateTime,
} from '../helpers'
import { SpAlert, SpEmpty, SpSection, SpStat } from '../ui'

export default function HomePage({
  refreshKey,
  onNavigate,
}: {
  refreshKey: number
  onNavigate: (page: 'assignments' | 'pulse' | 'marketplace' | 'support' | 'profile') => void
}) {
  const [home, setHome] = useState<HomeSummary | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    studentApi
      .home()
      .then((result) => {
        setHome(result)
        setError('')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load your home page.')
      })
  }, [])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  if (error) return <SpAlert tone="error">{error}</SpAlert>
  if (!home) return <div className="sp-loading">Loading your workspace…</div>

  return (
    <>
      <div className="sp-greeting">
        <h2>Hello, {home.student.full_name.split(' ')[0]}</h2>
        <p>
          {home.student.program} · {home.student.cohort} · {home.term}
        </p>
      </div>

      <div className="sp-stat-grid">
        <SpStat
          label="Attendance"
          value={
            home.attendance_percentage === null
              ? 'Not available'
              : `${home.attendance_percentage}%`
          }
          caption="Latest recorded value"
          tone="blue"
        />
        <SpStat
          label="Academic average"
          value={
            home.academic_average === null
              ? 'Not available'
              : `${home.academic_average}%`
          }
          caption="Latest recorded value"
          tone="mint"
        />
        <SpStat
          label="Due soon"
          value={String(home.due_soon_count)}
          caption={`${home.pending_assignments} awaiting grading`}
          tone="lavender"
        />
        <SpStat
          label="Pulse Points balance"
          value={String(home.pulse_balance)}
          caption={`${home.affordable_rewards} reward(s) affordable`}
          tone="mint"
        />
        <SpStat
          label="Completed assignments"
          value={String(home.completed_assignments)}
          caption="Graded so far"
          tone="blue"
        />
        <SpStat
          label="Lifetime earned"
          value={String(home.lifetime_earned)}
          caption="Net Pulse Points earned"
          tone="lavender"
        />
      </div>

      <div className="sp-two-col">
        <SpSection
          title="Upcoming deadlines"
          subtitle="Open assignments in your cohort, soonest first."
        >
          {home.upcoming_deadlines.length === 0 ? (
            <SpEmpty
              title="Nothing due right now."
              hint="New assignments appear here as soon as your teacher publishes them."
            />
          ) : (
            <ul className="sp-list">
              {home.upcoming_deadlines.map((item) => (
                <li key={item.assignment_id} className="sp-list-row">
                  <ClipboardList size={17} />
                  <div>
                    <strong>{item.title}</strong>
                    <span>{item.subject}</span>
                  </div>
                  <span className="sp-list-meta">
                    <CalendarClock size={14} /> {dueLabel(item.due_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            className="sp-button-secondary"
            onClick={() => onNavigate('assignments')}
          >
            Go to Assignments
          </button>
        </SpSection>

        <SpSection
          title="Recent feedback"
          subtitle="Released grades and comments from your teachers."
        >
          {home.recent_feedback.length === 0 ? (
            <SpEmpty
              title="No graded feedback yet."
              hint="Feedback appears here after your teacher grades and releases it."
            />
          ) : (
            <ul className="sp-list">
              {home.recent_feedback.map((item) => (
                <li key={item.submission_id} className="sp-list-row">
                  <Award size={17} />
                  <div>
                    <strong>{item.assignment_title ?? 'Assignment'}</strong>
                    <span>
                      {item.marks_obtained === null
                        ? 'Grade not available'
                        : `${item.marks_obtained} / ${item.max_marks ?? '—'} marks`}
                      {item.feedback ? ` — ${item.feedback}` : ''}
                    </span>
                  </div>
                  <span className="sp-list-meta">
                    {formatUtcDateTime(item.graded_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            className="sp-button-secondary"
            onClick={() => onNavigate('assignments')}
          >
            Open Assignments
          </button>
        </SpSection>
      </div>

      <div className="sp-two-col">
        <SpSection
          title="Achievements"
          subtitle="Earned from your real activity — never punitive."
        >
          {home.achievements.length === 0 ? (
            <SpEmpty
              title="No achievements yet."
              hint="Submit your first assignment to unlock one."
            />
          ) : (
            <ul className="sp-chip-list">
              {home.achievements.map((a) => (
                <li key={a.code} className="sp-chip sp-chip-mint">
                  <Trophy size={14} /> {a.title}
                </li>
              ))}
            </ul>
          )}
        </SpSection>

        <SpSection
          title="Recent notifications"
          subtitle={
            home.unread_notifications > 0
              ? `${home.unread_notifications} unread.`
              : 'You are all caught up.'
          }
        >
          {home.notifications.length === 0 ? (
            <SpEmpty title="No notifications yet." />
          ) : (
            <ul className="sp-list">
              {home.notifications.map((n) => (
                <li
                  key={n.id}
                  className={`sp-list-row ${n.is_read ? '' : 'sp-unread'}`}
                >
                  <Zap size={17} />
                  <div>
                    <strong>{n.title}</strong>
                    <span>{n.body}</span>
                  </div>
                  <span className="sp-list-meta">
                    {formatUtcDateTime(n.created_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </SpSection>
      </div>

      <SpSection
        title="Your support requests"
        subtitle="Human-reviewed requests. They never trigger automatic penalties."
        actions={
          <button
            type="button"
            className="sp-button-secondary"
            onClick={() => onNavigate('support')}
          >
            Help &amp; Support
          </button>
        }
      >
        {home.support_requests.length === 0 ? (
          <SpEmpty
            title="No support requests."
            hint="You can request an academic check-in, mentor support, or assignment clarification."
          />
        ) : (
          <ul className="sp-list">
            {home.support_requests.map((r) => (
              <li key={r.id} className="sp-list-row">
                <span className={`sp-badge sp-badge-${r.status === 'resolved' ? 'mint' : r.status === 'in_review' ? 'blue' : 'lavender'}`}>
                  {r.status === 'in_review' ? 'In review' : r.status}
                </span>
                <div>
                  <strong>{r.subject}</strong>
                  <span>
                    {SUPPORT_TYPE_LABELS[r.request_type] ?? r.request_type}
                  </span>
                </div>
                <span className="sp-list-meta">
                  {formatUtcDateTime(r.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SpSection>
    </>
  )
}
