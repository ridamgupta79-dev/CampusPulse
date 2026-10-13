import { useCallback, useEffect, useState } from 'react'
import { Bell, ShieldCheck, Trophy } from 'lucide-react'
import {
  studentApi,
  type AchievementItem,
  type NotificationsData,
  type StudentMe,
} from '../studentApi'
import {
  SpAlert,
  SpEmpty,
  SpSection,
} from '../ui'
import { formatUtcDateTime } from '../helpers'

export default function SettingsPage({
  refreshKey,
  refresh,
}: {
  refreshKey: number
  refresh: () => void
}) {
  const [me, setMe] = useState<StudentMe | null>(null)
  const [notifications, setNotifications] = useState<NotificationsData | null>(null)
  const [achievements, setAchievements] = useState<AchievementItem[] | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(() => {
    Promise.all([
      studentApi.me(),
      studentApi.notifications(),
      studentApi.achievements(),
    ])
      .then(([meResult, notificationsResult, achievementsResult]) => {
        setMe(meResult)
        setNotifications(notificationsResult)
        setAchievements(achievementsResult)
        setError('')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load settings.')
      })
  }, [])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  async function markAllRead() {
    try {
      const result = await studentApi.markAllNotificationsRead()
      setNotice(result.message)
      refresh()
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not update notifications.')
    }
  }

  if (error && !me) return <SpAlert tone="error">{error}</SpAlert>
  if (!me || !notifications || achievements === null) {
    return <div className="sp-loading">Loading settings…</div>
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
        title="Account"
        subtitle="Your session is verified by the backend on every request."
      >
        <dl className="sp-definition-grid">
          <div className="sp-definition">
            <dt>Signed in as</dt>
            <dd>{me.email}</dd>
          </div>
          <div className="sp-definition">
            <dt>Role</dt>
            <dd>Student</dd>
          </div>
          <div className="sp-definition">
            <dt>Linked student record</dt>
            <dd>
              {me.student.full_name} ({me.student.student_code})
            </dd>
          </div>
          <div className="sp-definition">
            <dt>Profile completion</dt>
            <dd>{me.profile_completion}%</dd>
          </div>
        </dl>
      </SpSection>

      <SpSection
        title="Notifications"
        subtitle={
          notifications.unread > 0
            ? `${notifications.unread} unread.`
            : 'You are all caught up.'
        }
        actions={
          <button
            type="button"
            className="sp-button-secondary"
            onClick={() => void markAllRead()}
            disabled={notifications.unread === 0}
          >
            <Bell size={15} /> Mark all as read
          </button>
        }
      >
        {notifications.notifications.length === 0 ? (
          <SpEmpty
            title="No notifications."
            hint="Awards, deadlines, and redemptions are announced here."
          />
        ) : (
          <ul className="sp-list">
            {notifications.notifications.map((item) => (
              <li
                key={item.id}
                className={`sp-list-row ${item.is_read ? '' : 'sp-unread'}`}
              >
                <Bell size={16} />
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.body}</span>
                </div>
                <span className="sp-list-meta">
                  {formatUtcDateTime(item.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SpSection>

      <SpSection
        title="Achievements"
        subtitle="Unlocked from your real activity. No streaks, no penalties."
      >
        {achievements.length === 0 ? (
          <SpEmpty
            title="No achievements yet."
            hint="Submit your first assignment to unlock 'First Assignment Submitted'."
          />
        ) : (
          <ul className="sp-list">
            {achievements.map((achievement) => (
              <li key={achievement.code} className="sp-list-row">
                <Trophy size={16} />
                <div>
                  <strong>{achievement.title}</strong>
                  <span>{achievement.description}</span>
                </div>
                <span className="sp-list-meta">
                  {formatUtcDateTime(achievement.earned_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SpSection>

      <SpSection
        title="Platform boundaries"
        subtitle="What this prototype does and does not do."
      >
        <ul className="sp-note-list">
          <li>
            <ShieldCheck size={14} /> Your role and data access are enforced by
            the backend from your signed-in session — never by the browser.
          </li>
          <li>
            <ShieldCheck size={14} /> Missing or restricted data is not evidence
            of poor performance.
          </li>
          <li>
            <ShieldCheck size={14} /> This prototype must not be used for
            automated punitive decisions.
          </li>
          <li>
            <ShieldCheck size={14} /> Marketplace vouchers are simulated and
            hold no real-world value.
          </li>
        </ul>
      </SpSection>
    </>
  )
}
