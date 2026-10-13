import { useCallback, useEffect, useState } from 'react'
import { CalendarClock, ChevronDown, Send } from 'lucide-react'
import {
  studentApi,
  type AssignmentDetail,
  type AssignmentListItem,
} from '../studentApi'
import { dueLabel, formatUtcDateTime } from '../helpers'
import {
  SpAlert,
  SpEmpty,
  SpSection,
  StateBadge,
} from '../ui'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'pending', label: 'To do' },
  { id: 'submitted', label: 'Submitted' },
  { id: 'graded', label: 'Graded' },
] as const

export default function AssignmentsPage({ refreshKey }: { refreshKey: number }) {
  const [filter, setFilter] = useState<string>('all')
  const [items, setItems] = useState<AssignmentListItem[] | null>(null)
  const [error, setError] = useState('')
  const [openId, setOpenId] = useState<number | null>(null)

  const load = useCallback(() => {
    studentApi
      .assignments(filter)
      .then((result) => {
        setItems(result)
        setError('')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load assignments.')
      })
  }, [filter])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  return (
    <>
      {error && (
        <SpAlert tone="error" onDismiss={() => setError('')}>
          {error}
        </SpAlert>
      )}

      <div className="sp-filter-row" role="tablist" aria-label="Assignment filters">
        {FILTERS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            role="tab"
            aria-selected={filter === entry.id}
            className={`sp-filter ${filter === entry.id ? 'sp-filter-active' : ''}`}
            onClick={() => setFilter(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </div>

      {items === null ? (
        <div className="sp-loading">Loading assignments…</div>
      ) : items.length === 0 ? (
        <SpSection title="Assignments" subtitle="No assignments match this filter.">
          <SpEmpty
            title="Nothing here yet."
            hint="Assignments published to your cohort by your teachers appear in this list."
          />
        </SpSection>
      ) : (
        <ul className="sp-assignment-list">
          {items.map((item) => (
            <li key={item.id} className="sp-assignment-card">
              <button
                type="button"
                className="sp-assignment-head"
                aria-expanded={openId === item.id}
                onClick={() => setOpenId(openId === item.id ? null : item.id)}
              >
                <div className="sp-assignment-title">
                  <strong>{item.title}</strong>
                  <span>
                    {item.subject}
                    {item.teacher_name ? ` · ${item.teacher_name}` : ''}
                  </span>
                </div>
                <div className="sp-assignment-meta">
                  <StateBadge state={item.submission_state} />
                  <span className="sp-list-meta">
                    <CalendarClock size={14} /> {dueLabel(item.due_at)}
                  </span>
                  <ChevronDown
                    size={17}
                    className={openId === item.id ? 'sp-rotated' : ''}
                  />
                </div>
              </button>
              {openId === item.id && (
                <AssignmentDetailPanel
                  assignmentId={item.id}
                  onSaved={() => void load()}
                  onError={setError}
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function AssignmentDetailPanel({
  assignmentId,
  onSaved,
  onError,
}: {
  assignmentId: number
  onSaved: () => void
  onError: (message: string) => void
}) {
  const [detail, setDetail] = useState<AssignmentDetail | null>(null)
  const [loadError, setLoadError] = useState('')
  const [textAnswer, setTextAnswer] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let cancelled = false
    studentApi
      .assignment(assignmentId)
      .then((result) => {
        if (cancelled) return
        setDetail(result)
        setTextAnswer(result.submission?.text_answer ?? '')
        setLinkUrl(result.submission?.link_url ?? '')
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : 'Could not load the assignment.')
        }
      })
    return () => {
      cancelled = true
    }
  }, [assignmentId])

  async function submit(asDraft: boolean) {
    if (!detail) return
    setBusy(true)
    setNotice('')
    try {
      const result = await studentApi.submitAssignment(
        detail.id,
        textAnswer.trim(),
        linkUrl.trim() || null,
        asDraft,
      )
      setDetail({ ...detail, submission: result.submission })
      setNotice(result.message)
      onSaved()
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Submission failed.')
    } finally {
      setBusy(false)
    }
  }

  if (loadError) return <SpAlert tone="error">{loadError}</SpAlert>
  if (!detail) return <div className="sp-loading">Loading assignment…</div>

  const submission = detail.submission
  const canEdit =
    submission === null ||
    submission.status === 'draft' ||
    submission.status === 'returned'
  const canSubmitNow =
    canEdit && detail.status === 'published' && detail.due_at !== undefined

  return (
    <div className="sp-assignment-body">
      <p className="sp-assignment-description">{detail.description}</p>
      {detail.instructions && (
        <p className="sp-assignment-instructions">
          <strong>Instructions: </strong>
          {detail.instructions}
        </p>
      )}
      <dl className="sp-definition-grid">
        <div className="sp-definition">
          <dt>Due (UTC)</dt>
          <dd>{formatUtcDateTime(detail.due_at)}</dd>
        </div>
        <div className="sp-definition">
          <dt>Maximum marks</dt>
          <dd>{detail.max_marks}</dd>
        </div>
        <div className="sp-definition">
          <dt>Late submissions</dt>
          <dd>
            {detail.allow_late_submissions
              ? `Allowed within ${detail.late_window_hours} h of the deadline (timing points capped at 1)`
              : 'Not allowed'}
          </dd>
        </div>
        <div className="sp-definition">
          <dt>Status</dt>
          <dd>{detail.status === 'published' ? 'Open' : 'Closed'}</dd>
        </div>
      </dl>

      {notice && (
        <SpAlert tone="success" onDismiss={() => setNotice('')}>
          {notice}
        </SpAlert>
      )}

      {submission && (
        <div className="sp-submission-summary">
          <h3>
            Your submission <StateBadge state={submission.status === 'submitted' && submission.is_late ? 'submitted_late' : submission.status} />
          </h3>
          <dl className="sp-definition-grid">
            <div className="sp-definition">
              <dt>Submitted at (UTC)</dt>
              <dd>{formatUtcDateTime(submission.submitted_at)}</dd>
            </div>
            <div className="sp-definition">
              <dt>Attempt</dt>
              <dd>
                {submission.resubmission_count === 0
                  ? 'First submission'
                  : `Resubmission #${submission.resubmission_count}`}
              </dd>
            </div>
            {submission.link_url && (
              <div className="sp-definition">
                <dt>Attached link</dt>
                <dd>{submission.link_url}</dd>
              </div>
            )}
          </dl>

          {submission.status === 'graded' ? (
            <>
              <dl className="sp-definition-grid">
                <div className="sp-definition">
                  <dt>Marks</dt>
                  <dd>
                    {submission.marks_obtained === null
                      ? 'Not available'
                      : `${submission.marks_obtained} / ${detail.max_marks}`}
                  </dd>
                </div>
                <div className="sp-definition">
                  <dt>Pulse Points breakdown</dt>
                  <dd>
                    Timing {submission.timing_points ?? 0} + Quality{' '}
                    {submission.quality_points ?? 0} ={' '}
                    {(submission.timing_points ?? 0) + (submission.quality_points ?? 0)}{' '}
                    (max 7)
                  </dd>
                </div>
                <div className="sp-definition">
                  <dt>Graded at (UTC)</dt>
                  <dd>{formatUtcDateTime(submission.graded_at)}</dd>
                </div>
              </dl>
              {submission.feedback_released && submission.feedback && (
                <p className="sp-feedback">
                  <strong>Teacher feedback: </strong>
                  {submission.feedback}
                </p>
              )}
            </>
          ) : submission.status === 'submitted' ? (
            <SpAlert tone="info">
              Awaiting grading. Your final Pulse Points are awarded after the
              teacher reviews quality — timing is recorded, the breakdown
              appears once the grade is released.
            </SpAlert>
          ) : submission.status === 'returned' ? (
            <SpAlert tone="info">
              The teacher returned this submission for revision. Update your
              answer below and submit again before the deadline rules close.
            </SpAlert>
          ) : null}
        </div>
      )}

      {canEdit && (
        <form
          className="sp-form"
          onSubmit={(event) => {
            event.preventDefault()
            void submit(false)
          }}
        >
          <label>
            {submission?.status === 'returned'
              ? 'Revised answer'
              : 'Your written answer'}
            <textarea
              value={textAnswer}
              onChange={(event) => setTextAnswer(event.target.value)}
              maxLength={20000}
              rows={5}
              placeholder="Type your answer here."
            />
          </label>
          <label>
            Reference link (optional)
            <input
              type="url"
              value={linkUrl}
              onChange={(event) => setLinkUrl(event.target.value)}
              maxLength={500}
              placeholder="https://…"
            />
          </label>
          <div className="sp-form-actions">
            <button
              type="submit"
              className="sp-button-primary"
              disabled={busy || detail.status !== 'published'}
              title={
                detail.status === 'published'
                  ? undefined
                  : 'This assignment is closed.'
              }
            >
              <Send size={15} /> {busy ? 'Submitting…' : 'Submit assignment'}
            </button>
            <button
              type="button"
              className="sp-button-secondary"
              disabled={busy}
              onClick={() => void submit(true)}
            >
              Save draft
            </button>
          </div>
          {canSubmitNow && (
            <p className="sp-form-hint">
              Submitting before the deadline earns up to 4 timing points based
              on when you submit. Quality points (up to 3) are added by your
              teacher when grading.
            </p>
          )}
          {detail.status !== 'published' && canEdit && (
            <SpAlert tone="info">
              This assignment is closed and no longer accepts submissions.
            </SpAlert>
          )}
        </form>
      )}

      {submission && submission.status === 'graded' && (
        <SpAlert tone="info">
          Graded submissions are final and cannot be edited.
        </SpAlert>
      )}
    </div>
  )
}
