import { useCallback, useEffect, useState } from 'react'
import { studentApi, type AcademicsData } from '../studentApi'
import { formatUtcDateTime } from '../helpers'
import { SpAlert, SpEmpty, SpSection, SpStat } from '../ui'

const DOMAIN_LABELS: Record<string, string> = {
  academics: 'Academics',
  attendance: 'Attendance',
  engagement: 'Engagement',
  wellbeing: 'Wellbeing signals you recorded',
}

export default function AcademicsPage({ refreshKey }: { refreshKey: number }) {
  const [data, setData] = useState<AcademicsData | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    studentApi
      .academics()
      .then((result) => {
        setData(result)
        setError('')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load your academics.')
      })
  }, [])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  if (error) return <SpAlert tone="error">{error}</SpAlert>
  if (!data) return <div className="sp-loading">Loading your academics…</div>

  const domains = Object.entries(data.domains)

  return (
    <>
      <div className="sp-stat-grid">
        <SpStat
          label="Latest attendance"
          value={
            data.latest_attendance === null
              ? 'Not available'
              : `${data.latest_attendance}%`
          }
          caption="Most recent recorded value"
          tone="blue"
        />
        <SpStat
          label="Assessment average"
          value={
            data.latest_average === null
              ? 'Not available'
              : `${data.latest_average}%`
          }
          caption="Most recent recorded value"
          tone="mint"
        />
        <SpStat
          label="Released grades"
          value={String(data.assignment_grades.length)}
          caption="Assignments graded and released"
          tone="lavender"
        />
      </div>

      <SpSection
        title="Released assignment grades"
        subtitle="Only grades your teacher has explicitly released appear here."
      >
        {data.assignment_grades.length === 0 ? (
          <SpEmpty
            title="No released grades yet."
            hint="When a teacher grades and releases your submission, it appears here."
          />
        ) : (
          <div className="sp-table-wrap">
            <table className="sp-table">
              <thead>
                <tr>
                  <th>Assignment</th>
                  <th>Subject</th>
                  <th>Marks</th>
                  <th>Timing / Quality points</th>
                  <th>Submitted</th>
                  <th>Feedback</th>
                </tr>
              </thead>
              <tbody>
                {data.assignment_grades.map((grade) => (
                  <tr key={grade.assignment_id}>
                    <td>
                      <strong>{grade.title}</strong>
                    </td>
                    <td>{grade.subject}</td>
                    <td>
                      {grade.marks_obtained === null
                        ? 'Not available'
                        : `${grade.marks_obtained} / ${grade.max_marks}`}
                    </td>
                    <td>
                      {grade.timing_points === null && grade.quality_points === null
                        ? 'Not available'
                        : `${grade.timing_points ?? 0} / ${grade.quality_points ?? 0}`}
                      {grade.is_late ? ' (late)' : ''}
                    </td>
                    <td>{formatUtcDateTime(grade.graded_at)}</td>
                    <td>{grade.feedback ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SpSection>

      {domains.length === 0 ? (
        <SpSection title="Recorded signals" subtitle="Your academic records.">
          <SpEmpty
            title="No academic records yet."
            hint="Attendance and assessment data appear here once your institution records it."
          />
        </SpSection>
      ) : (
        domains.map(([domain, signals]) => (
          <SpSection
            key={domain}
            title={DOMAIN_LABELS[domain] ?? domain}
            subtitle="Values come from your institution's records."
          >
            <div className="sp-table-wrap">
              <table className="sp-table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th>Value</th>
                    <th>Recorded (UTC)</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((signal, index) => (
                    <tr key={`${signal.signal_name}-${index}`}>
                      <td>{signal.signal_name.replaceAll('_', ' ')}</td>
                      <td>
                        {signal.numeric_value !== null
                          ? String(signal.numeric_value)
                          : signal.text_value ?? 'Not available'}
                      </td>
                      <td>{formatUtcDateTime(signal.recorded_at)}</td>
                      <td>{signal.source_label ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SpSection>
        ))
      )}

      <SpAlert tone="info">{data.note}</SpAlert>
    </>
  )
}
