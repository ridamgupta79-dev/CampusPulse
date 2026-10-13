import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { studentApi, type SupportRequestRecord } from '../studentApi'
import {
  SpAlert,
  SpEmpty,
  SpSection,
} from '../ui'
import { SUPPORT_TYPE_LABELS, formatUtcDateTime } from '../helpers'

const REQUEST_TYPES = [
  { id: 'academic_checkin', label: 'Academic check-in' },
  { id: 'mentor_support', label: 'Mentor support' },
  { id: 'assignment_clarification', label: 'Assignment clarification' },
] as const

export default function SupportPage({ refreshKey }: { refreshKey: number }) {
  const [requests, setRequests] = useState<SupportRequestRecord[] | null>(null)
  const [requestType, setRequestType] = useState<string>('academic_checkin')
  const [subject, setSubject] = useState('')
  const [details, setDetails] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    studentApi
      .supportRequests()
      .then((result) => setRequests(result))
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load your requests.')
      })
  }, [])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setNotice('')
    try {
      const result = await studentApi.createSupportRequest(
        requestType,
        subject.trim(),
        details.trim(),
      )
      setNotice(result.message)
      setSubject('')
      setDetails('')
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not submit your request.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {error && (
        <SpAlert tone="error" onDismiss={() => setError('')}>
          {error}
        </SpAlert>
      )}
      {notice && (
        <SpAlert tone="success" onDismiss={() => setNotice('')}>
          {notice}
        </SpAlert>
      )}

      <SpSection
        title="Request help"
        subtitle="A staff member reviews every request personally. Requests never trigger automatic penalties and are never used in risk scoring."
      >
        <form className="sp-form" onSubmit={(event) => void submit(event)}>
          <label>
            What kind of support do you need?
            <select
              value={requestType}
              onChange={(event) => setRequestType(event.target.value)}
            >
              {REQUEST_TYPES.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Subject
            <input
              type="text"
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              minLength={3}
              maxLength={150}
              required
              placeholder="One line summarising your request"
            />
          </label>
          <label>
            Details (optional)
            <textarea
              value={details}
              onChange={(event) => setDetails(event.target.value)}
              maxLength={4000}
              rows={5}
              placeholder="Add any context that would help the reviewer."
            />
          </label>
          <button type="submit" className="sp-button-primary" disabled={busy}>
            {busy ? 'Sending…' : 'Send request'}
          </button>
        </form>
      </SpSection>

      <SpSection
        title="Your requests"
        subtitle="Only you and the reviewing staff can see these. Internal staff notes are never shown to students."
      >
        {requests === null ? (
          <div className="sp-loading">Loading your requests…</div>
        ) : requests.length === 0 ? (
          <SpEmpty
            title="No support requests yet."
            hint="Use the form above to ask for academic, mentor, or assignment help."
          />
        ) : (
          <ul className="sp-list">
            {requests.map((request) => (
              <li key={request.id} className="sp-support-row">
                <div className="sp-support-head">
                  <span
                    className={`sp-badge sp-badge-${
                      request.status === 'resolved'
                        ? 'mint'
                        : request.status === 'in_review'
                          ? 'blue'
                          : 'lavender'
                    }`}
                  >
                    {request.status === 'in_review'
                      ? 'In review'
                      : request.status}
                  </span>
                  <strong>{request.subject}</strong>
                  <span className="sp-list-meta">
                    {SUPPORT_TYPE_LABELS[request.request_type] ??
                      request.request_type}{' '}
                    · {formatUtcDateTime(request.created_at)}
                  </span>
                </div>
                {request.details && <p>{request.details}</p>}
                {request.response && (
                  <p className="sp-feedback">
                    <strong>Staff response: </strong>
                    {request.response}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </SpSection>
    </>
  )
}
