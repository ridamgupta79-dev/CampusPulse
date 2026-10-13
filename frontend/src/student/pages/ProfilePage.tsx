import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { studentApi, type ProfileData } from '../studentApi'
import { SpAlert, SpSection, SpStat } from '../ui'
export default function ProfilePage({ refreshKey }: { refreshKey: number }) {
  const [data, setData] = useState<ProfileData | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)

  const [contactEmail, setContactEmail] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [bio, setBio] = useState('')
  const [skills, setSkills] = useState('')
  const [certifications, setCertifications] = useState('')

  const load = useCallback(() => {
    studentApi
      .profile()
      .then((result) => {
        setData(result)
        setContactEmail(result.profile.contact_email ?? '')
        setContactPhone(result.profile.contact_phone ?? '')
        setBio(result.profile.bio ?? '')
        setSkills(result.profile.skills ?? '')
        setCertifications(result.profile.certifications ?? '')
        setError('')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load your profile.')
      })
  }, [])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setNotice('')
    try {
      const result = await studentApi.updateProfile({
        contact_email: contactEmail.trim() || null,
        contact_phone: contactPhone.trim() || null,
        bio: bio.trim() || null,
        skills: skills.trim() || null,
        certifications: certifications.trim() || null,
      })
      setData((current) =>
        current
          ? { ...current, profile: result.profile, profile_completion: result.profile_completion }
          : current,
      )
      setNotice(result.message)
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save your profile.')
    } finally {
      setSaving(false)
    }
  }

  if (error && !data) return <SpAlert tone="error">{error}</SpAlert>
  if (!data) return <div className="sp-loading">Loading your profile…</div>

  const student = data.student
  const fields: Array<{ label: string; value: string | null }> = [
    { label: 'Student name', value: student.full_name },
    { label: 'Student code', value: student.student_code },
    { label: 'Program', value: student.program },
    { label: 'Department', value: student.department },
    { label: 'Year of study', value: String(student.year_of_study) },
    { label: 'Cohort', value: student.cohort },
    { label: 'Advisor', value: student.advisor_name },
    { label: 'Mentor', value: student.mentor_name },
  ]

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

      <div className="sp-stat-grid">
        <SpStat
          label="Profile completion"
          value={`${data.profile_completion}%`}
          caption="Add contact details and a short bio to reach 100%"
          tone="blue"
        />
        <SpStat
          label="Enrolled courses"
          value={String(data.enrolled_courses.length)}
          caption="From your academic records"
          tone="mint"
        />
      </div>

      <SpSection
        title="Student record"
        subtitle="Maintained by your institution. Ask your office to correct any errors — this view is read-only."
      >
        <dl className="sp-definition-grid">
          {fields.map((field) => (
            <div key={field.label} className="sp-definition">
              <dt>{field.label}</dt>
              <dd>{field.value ?? 'Not available'}</dd>
            </div>
          ))}
        </dl>
        {data.enrolled_courses.length > 0 && (
          <ul className="sp-chip-list">
            {data.enrolled_courses.map((course) => (
              <li key={course} className="sp-chip sp-chip-blue">
                {course}
              </li>
            ))}
          </ul>
        )}
      </SpSection>

      <SpSection
        title="Your portal profile"
        subtitle="Only you and authorized staff can see this. It is never shared with other students."
      >
        <form className="sp-form" onSubmit={(event) => void save(event)}>
          <label>
            Contact email
            <input
              type="email"
              value={contactEmail}
              onChange={(event) => setContactEmail(event.target.value)}
              maxLength={254}
              placeholder="you@example.com"
            />
          </label>
          <label>
            Contact phone
            <input
              type="tel"
              value={contactPhone}
              onChange={(event) => setContactPhone(event.target.value)}
              maxLength={30}
              placeholder="Optional"
            />
          </label>
          <label>
            Short bio
            <textarea
              value={bio}
              onChange={(event) => setBio(event.target.value)}
              maxLength={2000}
              rows={3}
              placeholder="Tell your mentors a little about your goals."
            />
          </label>
          <label>
            Skills
            <textarea
              value={skills}
              onChange={(event) => setSkills(event.target.value)}
              maxLength={2000}
              rows={2}
              placeholder="e.g. SQL, Python, public speaking"
            />
          </label>
          <label>
            Certifications
            <textarea
              value={certifications}
              onChange={(event) => setCertifications(event.target.value)}
              maxLength={2000}
              rows={2}
              placeholder="Any certifications you have earned"
            />
          </label>
          <button type="submit" className="sp-button-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </form>
      </SpSection>

      <SpSection
        title="Privacy note"
        subtitle="What your teachers and mentors can and cannot see."
      >
        <ul className="sp-note-list">
          <li>Staff can see this profile and your academic signals.</li>
          <li>Confidential counselling notes and internal risk assessments are never shown here.</li>
          <li>Other students can only see your name, cohort, and rank on the leaderboard — never your email or student code.</li>
        </ul>
      </SpSection>
    </>
  )
}
