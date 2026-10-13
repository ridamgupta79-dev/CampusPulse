import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  Bell,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  GraduationCap,
  Home,
  LifeBuoy,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Store,
  User,
  X,
  Zap,
} from 'lucide-react'
import {
  studentApi,
  type NotificationsData,
  type StudentMe,
} from './studentApi'
import { SpAlert } from './ui'
import './student.css'
import HomePage from './pages/HomePage'
import ProfilePage from './pages/ProfilePage'
import AcademicsPage from './pages/AcademicsPage'
import AssignmentsPage from './pages/AssignmentsPage'
import PulsePointsPage from './pages/PulsePointsPage'
import MarketplacePage from './pages/MarketplacePage'
import SupportPage from './pages/SupportPage'
import SettingsPage from './pages/SettingsPage'

type StudentPage =
  | 'home'
  | 'profile'
  | 'academics'
  | 'assignments'
  | 'pulse'
  | 'marketplace'
  | 'support'
  | 'settings'

const PAGE_TITLES: Record<StudentPage, { title: string; subtitle: string }> = {
  home: {
    title: 'Student Home',
    subtitle: 'Your day at a glance, from your own records.',
  },
  profile: {
    title: 'My Profile',
    subtitle: 'Your student record and personal portal profile.',
  },
  academics: {
    title: 'Academics',
    subtitle: 'Your recorded academic signals and released grades.',
  },
  assignments: {
    title: 'Assignments',
    subtitle: 'View, submit, and track your coursework.',
  },
  pulse: {
    title: 'My Pulse Points',
    subtitle: 'Your balance and the full transaction ledger behind it.',
  },
  marketplace: {
    title: 'Pulse Marketplace',
    subtitle: 'Redeem rewards and see how you rank on the leaderboard.',
  },
  support: {
    title: 'Help & Support',
    subtitle: 'Ask for help — every request is reviewed by a person.',
  },
  settings: {
    title: 'Settings',
    subtitle: 'Account, notifications, achievements, and boundaries.',
  },
}

const navigation: { id: StudentPage; label: string; icon: typeof Home }[] = [
  { id: 'home', label: 'Student Home', icon: Home },
  { id: 'profile', label: 'My Profile', icon: User },
  { id: 'academics', label: 'Academics', icon: BookOpen },
  { id: 'assignments', label: 'Assignments', icon: ClipboardList },
  { id: 'pulse', label: 'My Pulse Points', icon: Zap },
  { id: 'marketplace', label: 'Pulse Marketplace', icon: Store },
  { id: 'support', label: 'Help & Support', icon: LifeBuoy },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export default function StudentPortal({ onSignOut }: { onSignOut: () => void }) {
  const [page, setPage] = useState<StudentPage>('home')
  const [enrolled, setEnrolled] = useState<boolean | null>(null)
  const [me, setMe] = useState<StudentMe | null>(null)
  const [notifications, setNotifications] = useState<NotificationsData | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), [])

  useEffect(() => {
    let cancelled = false
    studentApi
      .linkStatus()
      .then((status) => {
        if (!cancelled) setEnrolled(status.linked)
      })
      .catch(() => {
        // A network or session error surfaces through the 401 handler; a
        // fresh account simply is not linked yet.
        if (!cancelled) setEnrolled(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (enrolled !== true) return
    let cancelled = false
    studentApi
      .me()
      .then((result) => {
        if (!cancelled) setMe(result)
      })
      .catch(() => {})
    studentApi
      .notifications()
      .then((result) => {
        if (!cancelled) setNotifications(result)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [enrolled, refreshKey])

  function changePage(next: StudentPage) {
    setPage(next)
    setMobileOpen(false)
  }

  if (enrolled === null) {
    return (
      <div className="sp-root sp-boot-screen">
        <GraduationCap size={28} />
        <p>Checking your enrollment…</p>
      </div>
    )
  }

  if (!enrolled) {
    return (
      <EnrollScreen
        onEnrolled={() => {
          setEnrolled(true)
          refresh()
        }}
        onSignOut={onSignOut}
      />
    )
  }

  return (
    <div className="app-shell sp-root">
      <aside className={`sp-sidebar ${mobileOpen ? 'sp-sidebar-open' : ''}`}>
        <div className="sp-brand">
          <div className="sp-brand-mark">
            <GraduationCap size={22} />
          </div>
          <div>
            <strong>CampusPulse</strong>
            <span>STUDENT PORTAL</span>
          </div>
          <button
            type="button"
            className="sp-mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X />
          </button>
        </div>

        <div className="sp-sidebar-label">MY LEARNING</div>

        <nav className="sp-nav" aria-label="Student portal">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`sp-nav-item ${page === id ? 'sp-nav-active' : ''}`}
              aria-current={page === id ? 'page' : undefined}
              onClick={() => changePage(id)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === 'settings' &&
                notifications &&
                notifications.unread > 0 && (
                  <span className="sp-nav-badge">{notifications.unread}</span>
                )}
            </button>
          ))}
          <button type="button" className="sp-nav-item sp-nav-logout" onClick={onSignOut}>
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </nav>

        <div className="sp-sidebar-bottom">
          <div className="sp-sidebar-bottom-icon">
            <ShieldCheck size={17} />
          </div>
          <div>
            <strong>Privacy-first</strong>
            <span>Your data stays within authorized views.</span>
          </div>
        </div>
      </aside>

      <main className="sp-main">
        <header className="sp-topbar">
          <button
            type="button"
            className="sp-mobile-menu"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu />
          </button>
          <div className="sp-topbar-title">
            <h1>{PAGE_TITLES[page].title}</h1>
            <p>{PAGE_TITLES[page].subtitle}</p>
          </div>
          <div className="sp-topbar-actions">
            {me && (
              <span className="sp-user-chip">
                <span className="sp-user-name">{me.student.full_name}</span>
                <span className="sp-user-code">{me.student.student_code}</span>
              </span>
            )}
            <button
              type="button"
              className="sp-button-secondary"
              onClick={() => changePage('settings')}
            >
              <Bell size={15} />
              {notifications && notifications.unread > 0 && (
                <span className="sp-nav-badge">{notifications.unread}</span>
              )}
            </button>
            <button type="button" className="sp-button-secondary" onClick={onSignOut}>
              <LogOut size={15} /> Logout
            </button>
          </div>
        </header>

        <div className="sp-content">
          <div className="sp-demo-banner">
            <ShieldCheck size={17} />
            <span>
              Prototype environment — every request is authorized by the backend
              from your signed-in account. Simulated rewards hold no real value.
            </span>
          </div>

          {page === 'home' && (
            <HomePage
              refreshKey={refreshKey}
              onNavigate={(next) => changePage(next)}
            />
          )}
          {page === 'profile' && <ProfilePage refreshKey={refreshKey} />}
          {page === 'academics' && <AcademicsPage refreshKey={refreshKey} />}
          {page === 'assignments' && <AssignmentsPage refreshKey={refreshKey} />}
          {page === 'pulse' && <PulsePointsPage refreshKey={refreshKey} />}
          {page === 'marketplace' && <MarketplacePage refreshKey={refreshKey} />}
          {page === 'support' && <SupportPage refreshKey={refreshKey} />}
          {page === 'settings' && (
            <SettingsPage refreshKey={refreshKey} refresh={refresh} />
          )}
        </div>
      </main>
    </div>
  )
}

function EnrollScreen({
  onEnrolled,
  onSignOut,
}: {
  onEnrolled: () => void
  onSignOut: () => void
}) {
  const [studentCode, setStudentCode] = useState('')
  const [enrollmentCode, setEnrollmentCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await studentApi.enroll(studentCode.trim().toUpperCase(), enrollmentCode.trim().toUpperCase())
      onEnrolled()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Enrollment failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="sp-root sp-boot-screen sp-enroll-screen">
      <section className="sp-enroll-card">
        <div className="sp-enroll-brand">
          <GraduationCap size={26} />
          <strong>CampusPulse Student Portal</strong>
        </div>
        <h1>One step left: link your account</h1>
        <p>
          Your sign-in is verified, but it is not yet connected to a student
          record. Ask your teacher or department office for a single-use
          enrollment code, then enter it below together with your student code.
        </p>
        <ul className="sp-note-list">
          <li>The code works exactly once and only for your student record.</li>
          <li>Guessing student codes never grants access — the code is required.</li>
        </ul>
        <form className="sp-form" onSubmit={(event) => void submit(event)}>
          <label>
            Student code
            <input
              type="text"
              value={studentCode}
              onChange={(event) => setStudentCode(event.target.value)}
              minLength={3}
              maxLength={30}
              required
              placeholder="e.g. CP-2026-0123"
            />
          </label>
          <label>
            Enrollment code
            <input
              type="text"
              value={enrollmentCode}
              onChange={(event) => setEnrollmentCode(event.target.value)}
              minLength={6}
              maxLength={64}
              required
              placeholder="e.g. CP-ABCD2345"
            />
          </label>
          {error && <SpAlert tone="error">{error}</SpAlert>}
          <button type="submit" className="sp-button-primary" disabled={busy}>
            <CheckCircle2 size={16} />
            {busy ? 'Linking…' : 'Complete enrollment'}
          </button>
        </form>
        <button type="button" className="sp-button-secondary" onClick={onSignOut}>
          <LogOut size={15} /> Sign out
        </button>
      </section>
    </div>
  )
}
