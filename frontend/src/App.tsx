import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  Activity,
  AlertTriangle,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  LayoutDashboard,
  Search,
  ShieldCheck,
  Users,
  X,
  RefreshCw,
  Clock3,
  Menu,
  Settings,
  ChevronRight,
  CircleCheck,
  CircleX,
  Eye,
  EyeOff,
  GraduationCap,
  ArrowRight,
} from 'lucide-react'
import {
  campusPulseApi,
  getAuthUser,
  logout,
  setUnauthorizedHandler,
  loginWithDatabase,
  registerWithDatabase,
  type DemoRole,
  type Student as ApiStudent,
  type Recommendation,
  type Intervention,
} from './api/campusPulseApi'
import StudentPortal from './student/StudentPortal'
import './App.css'

type Page =
  | 'Command Center'
  | 'Student 360'
  | 'Risk Assessments'
  | 'Recommendations'
  | 'Interventions'
  | 'Outcomes & Analytics'
  | 'Settings'

type StudentRow = ApiStudent & { code: string }

const navigation: { label: Page; icon: typeof LayoutDashboard }[] = [
  { label: 'Command Center', icon: LayoutDashboard },
  { label: 'Student 360', icon: Users },
  { label: 'Risk Assessments', icon: Activity },
  { label: 'Recommendations', icon: ClipboardCheck },
  { label: 'Interventions', icon: CalendarClock },
  { label: 'Outcomes & Analytics', icon: BookOpen },
  { label: 'Settings', icon: Settings },
]

const pageDescriptions: Record<Page, string> = {
  'Command Center': 'A central view of student support activity and follow-up.',
  'Student 360': 'Review available student information, consent, and permitted signals.',
  'Risk Assessments': 'Run explainable academic-support assessments for staff review.',
  Recommendations: 'Review proposed support actions before an intervention is assigned.',
  Interventions: 'Coordinate support, follow-up, and intervention status.',
  'Outcomes & Analytics': 'Review cohort coverage and recorded outcomes with appropriate caveats.',
  Settings: 'Review the current demo role and platform boundaries.',
}

function App() {
  const [page, setPage] = useState<Page>('Command Center')
  const [isSignedIn, setIsSignedIn] = useState(() => getAuthUser() !== null)
  const [loginEmail, setLoginEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [loginPassword, setLoginPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loginError, setLoginError] = useState('')
  const [students, setStudents] = useState<StudentRow[]>([])
  const [query, setQuery] = useState('')
  const [role, setRole] = useState<DemoRole>(() => getAuthUser()?.role ?? 'hod')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [profile, setProfile] = useState<
    Awaited<ReturnType<typeof campusPulseApi.getStudent360>> | null
  >(null)
  const [analytics, setAnalytics] = useState<
    Awaited<ReturnType<typeof campusPulseApi.getCohortAnalytics>> | null
  >(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [assessmentResult, setAssessmentResult] = useState<Record<string, unknown> | null>(null)
  const [assessmentBusy, setAssessmentBusy] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const loadStudents = useCallback(async () => {
    setLoading(true)
    try {
      const result = await campusPulseApi.getStudents()
      setStudents(result.map((student) => ({
        ...student,
        code: student.student_code,
      })))
      setSelectedId((current) => current ?? result[0]?.id ?? null)
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load students.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // The backend rejects expired or invalid sessions with 401; return the
    // user to the sign-in screen when that happens.
    setUnauthorizedHandler(() => {
      setIsSignedIn(false)
      setNotice('')
      setLoginError('Your session has expired. Please sign in again.')
    })
  }, [])

  useEffect(() => {
    if (!isSignedIn || role === 'student') return
    void loadStudents()
  }, [loadStudents, isSignedIn, role])

  useEffect(() => {
    if (page !== 'Student 360' || selectedId === null || role === 'student') return

    let cancelled = false
    setLoading(true)
    setProfile(null)

    campusPulseApi.getStudent360(selectedId)
      .then((data) => {
        if (!cancelled) {
          setProfile(data)
          setError('')
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Could not load student profile.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [page, selectedId, role, refreshKey])

  useEffect(() => {
    if (
      (page !== 'Outcomes & Analytics' && page !== 'Command Center') ||
      role === 'student'
    ) {
      return
    }

    let cancelled = false

    campusPulseApi.getCohortAnalytics()
      .then((data) => {
        if (!cancelled) setAnalytics(data)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Could not load cohort analytics.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [page, role, refreshKey])

  const filtered = students.filter((student) =>
    `${student.full_name} ${student.student_code} ${student.program} ${student.department}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  )

  async function runAssessment() {
    if (selectedId === null) {
      setNotice('Select a student first.')
      return
    }

    setAssessmentBusy(true)
    setAssessmentResult(null)
    setError('')

    try {
      const body = await campusPulseApi.runAcademicAssessment(selectedId)
      setAssessmentResult(body)
      setNotice('Assessment completed. Review the returned evidence before acting.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Assessment request failed.')
    } finally {
      setAssessmentBusy(false)
    }
  }

  function changePage(next: Page) {
    setPage(next)
    setMobileOpen(false)
    setError('')
    setNotice('')
  }

  async function refreshWorkspace() {
    setRefreshKey((current) => current + 1)
    await loadStudents()
    setNotice('Workspace refresh requested.')
  }

  if (!isSignedIn) {
    const roleNames: Record<DemoRole, string> = {
      student: 'Student',
      hod: 'Head of Department (HOD)',
      faculty: 'Faculty / Advisor',
      mentor: 'Student Mentor',
      counsellor: 'Counsellor',
      finance: 'Finance Team',
      placement: 'Placement Team',
    }

    async function handleLogin(event: FormEvent<HTMLFormElement>) {
      event.preventDefault()
      setLoginError('')
      try {
        const result = authMode === 'register'
          ? await registerWithDatabase(fullName.trim(), loginEmail.trim(), loginPassword, role)
          : await loginWithDatabase(loginEmail.trim(), loginPassword, role)
        setRole(result.user.role)
        setIsSignedIn(true)
        setNotice(authMode === 'register' ? `Account created. Signed in as ${roleNames[result.user.role]}.` : `Signed in as ${roleNames[result.user.role]}.`)
      } catch (error) {
        setLoginError(error instanceof Error ? error.message : 'Could not connect to the API server.')
      }
    }

    return (
      <main className="cp-login-page">
        <div className="cp-login-orb cp-login-orb-one" />
        <div className="cp-login-orb cp-login-orb-two" />
        <section className="cp-login-card" aria-labelledby="cp-login-title">
          <div className="cp-login-brand">
            <img src="/campuspulse-mark.png" alt="CampusPulse logo" />
            <div className="cp-login-brand-name">Campus<span>Pulse</span></div>
            <div className="cp-login-brand-caption">STUDENT SUCCESS INTELLIGENCE</div>
          </div>

          <div className="cp-login-intro">
            <span className="cp-login-eyebrow"><span /> STUDENT SUCCESS WORKSPACE</span>
            <h1 id="cp-login-title">{authMode === 'register' ? 'Create your account' : 'Welcome back'}</h1>
            <p>{authMode === 'register' ? 'Create a CampusPulse account to access your student-support workspace.' : 'Sign in to coordinate student support, track interventions, and measure outcomes.'}</p>
          </div>

          <form className="cp-login-form" onSubmit={handleLogin}>
            {authMode === 'register' && <>
              <label className="cp-login-label" htmlFor="cp-login-name">Full name</label>
              <input id="cp-login-name" type="text" autoComplete="name" placeholder="Enter your full name" value={fullName} onChange={(event) => setFullName(event.target.value)} minLength={2} maxLength={120} required />
            </>}
            <label className="cp-login-label" htmlFor="cp-login-email">Email address</label>
            <input
              id="cp-login-email"
              type="email"
              autoComplete="username"
              placeholder="you@institution.edu"
              value={loginEmail}
              onChange={(event) => setLoginEmail(event.target.value)}
              required
            />

            <label className="cp-login-label cp-login-label-spaced" htmlFor="cp-login-password">Password</label>
            <div className="cp-password-wrap">
              <input
                id="cp-login-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete={authMode === 'register' ? 'new-password' : 'current-password'}
                minLength={authMode === 'register' ? 8 : undefined}
                placeholder={authMode === 'register' ? 'Create a password (8+ characters)' : 'Enter your password'}
                value={loginPassword}
                onChange={(event) => setLoginPassword(event.target.value)}
                required
              />
              <button type="button" className="cp-password-toggle" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>

            <label className="cp-login-label cp-login-label-spaced" htmlFor="cp-login-role">Sign in as</label>
            <div className="cp-role-select-wrap">
              <GraduationCap size={20} />
              <select id="cp-login-role" value={role} onChange={(event) => setRole(event.target.value as DemoRole)}>
                {Object.entries(roleNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </div>

            {loginError && <div className="cp-login-error" role="alert">{loginError}</div>}

            <button type="submit" className="cp-login-submit">
              {authMode === 'register' ? 'Create account' : 'Sign in to CampusPulse'} <ArrowRight size={19} />
            </button>
          </form>

          <div className="cp-login-divider"><span /></div>
          <div className="cp-login-switch">
            {authMode === 'login' ? <>
              <span>New to CampusPulse?</span>
              <button type="button" onClick={() => { setAuthMode('register'); setLoginError('') }}>Create an account</button>
            </> : <>
              <span>Already have an account?</span>
              <button type="button" onClick={() => { setAuthMode('login'); setLoginError('') }}>Sign in</button>
            </>}
          </div>
          <div className="cp-login-demo-note">
            <ShieldCheck size={18} />
            <p><strong>Prototype account security</strong><br />Accounts are stored in local SQLite and passwords are salted and hashed. Signed-in sessions use expiring tokens that the backend validates on every request. This remains a prototype: do not use real student data or deploy publicly.</p>
          </div>
          <div className="cp-login-footer">© 2026 CampusPulse <span>•</span> Responsible student support</div>
        </section>
      </main>
    )
  }

  // Student accounts get a dedicated portal shell; the role comes from the
  // backend-verified session, never from browser-controlled state.
  if (role === 'student') {
    return (
      <StudentPortal
        onSignOut={() => {
          logout()
          setIsSignedIn(false)
          setLoginEmail('')
          setLoginPassword('')
          setLoginError('')
          setProfile(null)
          setAnalytics(null)
          setStudents([])
          setNotice('')
          setError('')
        }}
      />
    )
  }

  return (
    <div className="app-shell fast-app">
      <aside className={`sidebar ${mobileOpen ? 'fast-sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark brand-logo-wrap">
            <img src="/campuspulse-mark.png" alt="" className="brand-logo" />
          </div>
          <div>
            <strong>CampusPulse</strong>
            <span>EDUCATION INTELLIGENCE</span>
          </div>
          <button
            className="fast-mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X />
          </button>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-item ${page === label ? 'nav-active' : ''}`}
              aria-current={page === label ? 'page' : undefined}
              onClick={() => changePage(label)}
            >
              <Icon size={19} />
              <span>{label}</span>
              {page === label && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom fast-sidebar-bottom">
          <div className="fast-sidebar-bottom-icon"><ShieldCheck size={18} /></div>
          <div>
            <strong>Privacy-first support</strong>
            <span>Review consent and data quality before acting.</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="fast-mobile-menu"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu />
          </button>

          <label className="global-search">
            <Search size={17} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search students, student codes, programs…"
              aria-label="Search students"
            />
            <kbd>⌘ K</kbd>
          </label>

          <div className="fast-top-actions">
            <label className="fast-role">
              <span>Signed-in role</span>
              <select
                value={role}
                disabled
                aria-readonly="true"
              >
                <option value="hod">HOD</option>
                <option value="faculty">Faculty</option>
                <option value="mentor">Mentor</option>
                <option value="counsellor">Counsellor</option>
                <option value="finance">Finance</option>
                <option value="placement">Placement</option>
              </select>
            </label>

            <button
              className="button-secondary fast-refresh"
              onClick={() => void refreshWorkspace()}
            >
              <RefreshCw size={16} /> Refresh
            </button>

            <button
              className="button-secondary fast-refresh"
              onClick={() => {
                logout()
                setIsSignedIn(false)
                setLoginEmail('')
                setLoginPassword('')
                setLoginError('')
                setProfile(null)
                setAnalytics(null)
                setStudents([])
                setNotice('')
                setError('')
              }}
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="live-dot" /> CAMPUSPULSE WORKSPACE
              </div>
              <h1>{page}</h1>
              <p className="page-subtitle">{pageDescriptions[page]}</p>
            </div>
          </div>

          <div className="demo-banner">
            <div className="demo-banner-icon">
              <ShieldCheck size={18} />
            </div>
            <div>
              <strong>Prototype / demonstration environment</strong>
              <span>
                Every request is authenticated and authorized by the backend from
                your signed-in account. Missing or restricted data is
                not evidence of poor performance. Do not use this prototype for
                automated punitive decisions.
              </span>
            </div>
          </div>

          {error && (
            <div className="fast-alert fast-alert-error" role="alert">
              <AlertTriangle size={18} />
              <span>{error}</span>
              <button onClick={() => setError('')} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}

          {notice && (
            <div className="fast-alert" role="status">
              <CheckCircle2 size={18} />
              <span>{notice}</span>
              <button onClick={() => setNotice('')} aria-label="Dismiss message">
                <X size={16} />
              </button>
            </div>
          )}

          {page === 'Command Center' && (
            <>
              <section className="metric-grid">
                <Metric
                  label="Students"
                  value={loading ? '…' : String(students.length)}
                  caption="Loaded from API"
                  icon={<Users size={19} />}
                />
                <Metric
                  label="Assessment workflow"
                  value="Ready"
                  caption="Requires staff review"
                  icon={<Activity size={19} />}
                />
                <Metric
                  label="Signed-in role"
                  value={role.toUpperCase()}
                  caption="Enforced by the backend"
                  icon={<ShieldCheck size={19} />}
                />
                <Metric
                  label="Recorded outcomes"
                  value={analytics ? String(analytics.outcome_coverage.recorded_outcomes) : '—'}
                  caption="From cohort analytics"
                  icon={<BookOpen size={19} />}
                />
              </section>

              <section className="dashboard-middle-grid">
                <div className="panel dashboard-panel dashboard-risk-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Risk distribution</h2>
                      <p>Recorded assessment categories across the current cohort.</p>
                    </div>
                    <button className="text-button" onClick={() => changePage('Risk Assessments')}>Review <ChevronRight size={15} /></button>
                  </div>
                  {analytics && Object.keys(analytics.risk_distribution).length > 0 ? (
                    <div className="dashboard-bars">
                      {Object.entries(analytics.risk_distribution).map(([label, count]) => {
                        const maxCount = Math.max(1, ...Object.values(analytics.risk_distribution))
                        return (
                          <div className="dashboard-bar-row" key={label}>
                            <div className="dashboard-bar-label"><span>{label.replaceAll('_', ' ')}</span><strong>{count}</strong></div>
                            <div className="dashboard-bar-track"><span className={`dashboard-bar-fill dashboard-bar-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`} style={{ width: `${Math.max(count > 0 ? 5 : 0, (count / maxCount) * 100)}%` }} /></div>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="dashboard-empty">No assessment distribution is available yet. Run an assessment to populate this view.</div>
                  )}
                  <div className="dashboard-panel-foot"><Activity size={15} /> Counts reflect recorded assessments, not a diagnosis or final decision.</div>
                </div>

                <div className="panel dashboard-panel dashboard-quality-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Data quality</h2>
                      <p>Check coverage before interpreting student signals.</p>
                    </div>
                    <span className="dashboard-mini-icon"><ShieldCheck size={17} /></span>
                  </div>
                  {analytics ? (
                    <>
                      <div className="quality-stat-grid">
                        <div><span>Signals examined</span><strong>{analytics.data_quality.signals_examined}</strong></div>
                        <div><span>Missing signals</span><strong>{analytics.data_quality.missing_signals}</strong></div>
                        <div><span>Stale signals</span><strong>{analytics.data_quality.stale_signals}</strong></div>
                        <div><span>Without assessment</span><strong>{analytics.assessment_coverage.students_without_assessment}</strong></div>
                      </div>
                      <p className="quality-note">{analytics.data_quality.note || analytics.interpretation_note}</p>
                    </>
                  ) : (
                    <div className="dashboard-empty">Waiting for the cohort analytics API.</div>
                  )}
                </div>
              </section>

              <section className="dashboard-bottom-grid">
                <div className="panel dashboard-panel dashboard-students-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Student directory</h2>
                      <p>Open a student record to review permitted information.</p>
                    </div>
                    <button className="text-button" onClick={() => changePage('Student 360')}>Student 360 <ChevronRight size={15} /></button>
                  </div>
                  <StudentTable
                    students={filtered}
                    query={query}
                    setQuery={setQuery}
                    loading={loading}
                    onSelect={(student) => {
                      setSelectedId(student.id)
                      changePage('Student 360')
                    }}
                  />
                </div>

                <div className="panel dashboard-panel dashboard-workload-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Intervention workload</h2>
                      <p>Follow-up status from recorded interventions.</p>
                    </div>
                    <CalendarClock size={18} className="dashboard-heading-icon" />
                  </div>
                  {analytics ? (
                    <>
                      <div className="workload-total"><strong>{analytics.intervention_workload.total}</strong><span>Total interventions</span></div>
                      <div className="workload-status-list">
                        {Object.entries(analytics.intervention_workload.by_status).map(([status, count]) => (
                          <div key={status}><span>{status.replaceAll('_', ' ')}</span><strong>{count}</strong></div>
                        ))}
                      </div>
                      <div className={`overdue-callout ${analytics.intervention_workload.overdue_open_interventions > 0 ? 'has-overdue' : ''}`}>
                        <Clock3 size={16} />
                        <span>{analytics.intervention_workload.overdue_open_interventions} overdue open interventions</span>
                      </div>
                    </>
                  ) : <div className="dashboard-empty">Intervention data will appear when analytics loads.</div>}
                  <button className="button-secondary dashboard-full-button" onClick={() => changePage('Interventions')}>Manage interventions <ChevronRight size={15} /></button>
                </div>

                <div className="panel dashboard-panel dashboard-actions-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Quick actions</h2>
                      <p>Continue the student support workflow.</p>
                    </div>
                  </div>
                  <button className="button-primary dashboard-action-button" onClick={() => changePage('Risk Assessments')}><Activity size={16} /> Run assessment</button>
                  <button className="button-secondary dashboard-action-button" onClick={() => changePage('Recommendations')}><ClipboardCheck size={16} /> Review recommendations</button>
                  <button className="button-secondary dashboard-action-button" onClick={() => changePage('Interventions')}><CalendarClock size={16} /> Follow up interventions</button>
                  <button className="button-secondary dashboard-action-button" onClick={() => changePage('Outcomes & Analytics')}><BookOpen size={16} /> View cohort analytics</button>
                </div>
              </section>
            </>
          )}

          {page === 'Student 360' && (
            <section className="panel fast-panel">
              <div className="panel-heading">
                <div>
                  <h2>Student profile</h2>
                  <p>
                    Displayed signals depend on the current role and consent rules.
                  </p>
                </div>
              </div>

              <div className="fast-toolbar">
                <label>
                  Student
                  <select
                    value={selectedId ?? ''}
                    onChange={(event) => setSelectedId(
                      event.target.value ? Number(event.target.value) : null,
                    )}
                  >
                    <option value="">Select a student</option>
                    {students.map((student) => (
                      <option key={student.id} value={student.id}>
                        {student.full_name} · {student.student_code}
                      </option>
                    ))}
                  </select>
                </label>
                <span className="fast-role-note">Viewing as {role}</span>
              </div>

              {loading && <p className="fast-muted">Loading consent-aware profile…</p>}

              {!loading && !profile && (
                <div className="fast-empty">
                  {selectedId === null
                    ? 'Select a student to view their profile.'
                    : 'No profile loaded. Check the API response or refresh.'}
                </div>
              )}

              {profile && (
                <>
                  <div className="fast-profile-header">
                    <div className="fast-avatar">
                      {profile.student.full_name
                        .split(' ')
                        .map((part) => part[0])
                        .join('')
                        .slice(0, 2)}
                    </div>
                    <div>
                      <h2>{profile.student.full_name}</h2>
                      <p>
                        {profile.student.student_code} · {profile.student.program} ·{' '}
                        {profile.student.department}
                      </p>
                    </div>
                    <span className="fast-chip">{profile.viewer_role} view</span>
                  </div>

                  <div className="fast-subheading">
                    <h3>Consent status</h3>
                    <span>Purpose-specific permissions</span>
                  </div>

                  <div className="fast-consent-grid">
                    {profile.consents.map((consent) => (
                      <div className="fast-consent" key={consent.purpose}>
                        <span>{consent.purpose.replaceAll('_', ' ')}</span>
                        <strong className={`fast-status fast-status-${consent.status}`}>
                          {consent.status.replaceAll('_', ' ')}
                        </strong>
                        <small>
                          Recorded {new Date(consent.recorded_at).toLocaleDateString()}
                        </small>
                      </div>
                    ))}
                  </div>

                  <div className="fast-subheading">
                    <h3>Permitted signals</h3>
                    <span>{profile.signals.length} returned by API</span>
                  </div>

                  {profile.signals.length === 0 ? (
                    <div className="fast-empty">
                      No signals are available to this role under the current consent
                      settings. This is not evidence of negative performance.
                    </div>
                  ) : (
                    <div className="fast-table-wrap">
                      <table className="fast-table">
                        <thead>
                          <tr>
                            <th>Signal</th>
                            <th>Domain</th>
                            <th>Value</th>
                            <th>Quality</th>
                            <th>Recorded</th>
                          </tr>
                        </thead>
                        <tbody>
                          {profile.signals.map((signal) => (
                            <tr key={signal.id}>
                              <td>{signal.signal_name}</td>
                              <td>{signal.domain}</td>
                              <td>
                                {signal.numeric_value ?? signal.text_value ?? 'Unavailable'}
                              </td>
                              <td><span className="fast-chip">{signal.quality_status}</span></td>
                              <td>{new Date(signal.recorded_at).toLocaleDateString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </section>
          )}

          {page === 'Risk Assessments' && (
            <>
              <section className="metric-grid">
                <Metric
                  label="Student records"
                  value={loading ? '…' : students.length.toLocaleString()}
                  caption="Available from the backend"
                  icon={<Users size={19} />}
                />
                <Metric
                  label="Selected student"
                  value={selectedId === null ? 'None' : `#${selectedId}`}
                  caption="Choose a record to assess"
                  icon={<Activity size={19} />}
                />
                <Metric
                  label="Decision policy"
                  value="Human-led"
                  caption="Assessment is not a diagnosis"
                  icon={<ShieldCheck size={19} />}
                />
              </section>
              <section className="risk-guidance-grid">
                <article className="panel risk-guidance-card">
                  <div className="risk-guidance-icon"><Activity size={19} /></div>
                  <h2>Explainable review, not prediction theatre</h2>
                  <p>The assessment uses the evidence returned by the backend. Review the contributing signals and data-quality caveats before deciding whether support is appropriate.</p>
                  <div className="risk-guidance-tags">
                    <span>Attendance</span><span>Academics</span><span>Data quality</span>
                  </div>
                </article>
                <article className="panel risk-guidance-card">
                  <div className="risk-guidance-icon"><ShieldCheck size={19} /></div>
                  <h2>Responsible action</h2>
                  <p>A result is a prompt for staff context and review. Missing or stale signals must remain unknown, and the system must not trigger punishment automatically.</p>
                  <div className="risk-guidance-foot"><CheckCircle2 size={16} /> Human review required before support is assigned</div>
                </article>
              </section>
            <section className="panel fast-panel">
              <div className="panel-heading">
                <div>
                  <h2>Academic-support assessment</h2>
                  <p>Run the existing backend assessment rule for a selected student.</p>
                </div>
                <span className="fast-chip">Staff review required</span>
              </div>

              <div className="fast-toolbar">
                <label>
                  Student
                  <select
                    value={selectedId ?? ''}
                    onChange={(event) => setSelectedId(
                      event.target.value ? Number(event.target.value) : null,
                    )}
                  >
                    <option value="">Select a student</option>
                    {students.map((student) => (
                      <option key={student.id} value={student.id}>
                        {student.full_name} · {student.student_code}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="button-primary"
                  disabled={assessmentBusy || selectedId === null}
                  onClick={() => void runAssessment()}
                >
                  {assessmentBusy ? 'Running…' : 'Run assessment'}
                </button>
              </div>

              <div className="fast-note">
                <AlertTriangle size={18} />
                <span>
                  Assessment uses available, valid, current signals and consent.
                  Missing or stale signals should not be interpreted as negative evidence.
                </span>
              </div>

              {assessmentResult && <AssessmentReport data={assessmentResult} />}
            </section>
            </>
          )}

          {page === 'Recommendations' && (
            <RecommendationWorkspace
              role={role}
              refreshKey={refreshKey}
              onNotice={setNotice}
              onError={setError}
              onChanged={() => setRefreshKey((key) => key + 1)}
            />
          )}

          {page === 'Interventions' && (
            <InterventionWorkspace
              role={role}
              refreshKey={refreshKey}
              onNotice={setNotice}
              onError={setError}
            />
          )}

          {page === 'Outcomes & Analytics' && (
            <section className="panel fast-panel">
              <div className="panel-heading">
                <div>
                  <h2>Cohort analytics</h2>
                  <p>Coverage and workload figures from the analytics endpoint.</p>
                </div>
                <span className="fast-chip">{analytics?.cohort ?? 'All cohorts'}</span>
              </div>

              {!analytics && (
                <p className="fast-muted">Analytics will appear when the API responds.</p>
              )}

              {analytics && (
                <>
                  <section className="metric-grid">
                    <Metric
                      label="Students"
                      value={String(analytics.student_count)}
                      caption="In selected cohort"
                      icon={<Users size={19} />}
                    />
                    <Metric
                      label="Assessed"
                      value={String(analytics.assessment_coverage.assessed_students)}
                      caption={`${analytics.assessment_coverage.students_without_assessment} without assessment`}
                      icon={<Activity size={19} />}
                    />
                    <Metric
                      label="Overdue interventions"
                      value={String(analytics.intervention_workload.overdue_open_interventions)}
                      caption={`${analytics.intervention_workload.total} total interventions`}
                      icon={<Clock3 size={19} />}
                    />
                    <Metric
                      label="Recorded outcomes"
                      value={String(analytics.outcome_coverage.recorded_outcomes)}
                      caption="Evidence quality varies"
                      icon={<BookOpen size={19} />}
                    />
                  </section>

                  <div className="fast-subheading">
                    <h3>Risk distribution</h3>
                    <span>Assessment coverage matters</span>
                  </div>

                  <div className="fast-bars">
                    {Object.entries(analytics.risk_distribution).map(([name, count]) => (
                      <div className="fast-bar-row" key={name}>
                        <span>{name.replaceAll('_', ' ')}</span>
                        <div className="fast-bar-track">
                          <div
                            className="fast-bar"
                            style={{
                              width: `${analytics.student_count
                                ? Math.min(100, count / analytics.student_count * 100)
                                : 0}%`,
                            }}
                          />
                        </div>
                        <strong>{count}</strong>
                      </div>
                    ))}
                  </div>

                  <p className="fast-muted">{analytics.interpretation_note}</p>
                  <p className="fast-muted">{analytics.data_quality.note}</p>
                </>
              )}
            </section>
          )}

          {page === 'Settings' && (
            <section className="panel fast-panel">
              <div className="panel-heading">
                <div>
                  <h2>Workspace settings</h2>
                  <p>Review the active demonstration configuration.</p>
                </div>
                <Settings size={22} />
              </div>

              <div className="fast-settings-grid">
                <div className="fast-consent">
                  <span>Signed-in account</span>
                  <strong>{getAuthUser()?.email ?? 'Unknown'}</strong>
                  <small>Authenticated against the backend database.</small>
                </div>
                <div className="fast-consent">
                  <span>Account role</span>
                  <strong>{role.toUpperCase()}</strong>
                  <small>Enforced by the backend on every API request.</small>
                </div>
                <div className="fast-consent">
                  <span>Backend API</span>
                  <strong>CampusPulse API</strong>
                  <small>Requests use the frontend /api proxy.</small>
                </div>
                <div className="fast-consent">
                  <span>Student records</span>
                  <strong>{students.length} loaded</strong>
                  <small>Loaded from the existing backend.</small>
                </div>
              </div>

              <div className="fast-subheading">
                <h3>Change role</h3>
                <span>Roles are tied to accounts and enforced by the backend</span>
              </div>

              <div className="fast-toolbar">
                <span className="fast-muted">
                  To act as another role, sign out and sign in with the
                  corresponding account. Client-side role switching cannot change
                  what the backend authorizes.
                </span>
                <button
                  className="button-secondary"
                  onClick={() => void refreshWorkspace()}
                >
                  <RefreshCw size={16} /> Refresh workspace
                </button>
              </div>

              <div className="fast-note">
                <ShieldCheck size={18} />
                <span>
                  This prototype should support human review. Missing data or restricted
                  signals must not be treated as proof of poor student performance.
                </span>
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  )
}

function Metric({
  label,
  value,
  caption,
  icon,
}: {
  label: string
  value: string
  caption: string
  icon: React.ReactNode
}) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <strong className="metric-value">{value}</strong>
      <span className="metric-caption">{caption}</span>
    </div>
  )
}

function StudentTable({
  students,
  query,
  setQuery,
  loading,
  onSelect,
}: {
  students: StudentRow[]
  query: string
  setQuery: (value: string) => void
  loading: boolean
  onSelect: (student: StudentRow) => void
}) {
  const [requestedPage, setRequestedPage] = useState(1)
  const pageSize = 10
  const pageCount = Math.max(1, Math.ceil(students.length / pageSize))
  const currentPage = Math.min(requestedPage, pageCount)
  const pageStudents = students.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  return (
    <>
      <label className="fast-search">
        <Search size={17} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search name, student code, or program…"
        />
        <button onClick={() => setQuery('')} aria-label="Clear search">
          <X size={16} />
        </button>
      </label>

      {loading && <p className="fast-muted">Loading students…</p>}

      <div className="fast-table-wrap">
        <table className="fast-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Program</th>
              <th>Department</th>
              <th>Year</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {pageStudents.map((student) => (
              <tr key={student.id}>
                <td>
                  <strong>{student.full_name}</strong>
                  <small className="fast-cell-sub">{student.student_code}</small>
                </td>
                <td>{student.program}</td>
                <td>{student.department}</td>
                <td>{student.year_of_study}</td>
                <td>
                  <button className="fast-link" onClick={() => onSelect(student)}>
                    Open profile ↗
                  </button>
                </td>
              </tr>
            ))}

            {!loading && students.length === 0 && (
              <tr>
                <td colSpan={5} className="fast-empty">No matching students found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {students.length > pageSize && (
        <div className="student-pagination">
          <span>
            Showing {(currentPage - 1) * pageSize + 1}–
            {Math.min(currentPage * pageSize, students.length)} of {students.length} students
          </span>
          <div>
            <button
              className="button-secondary"
              disabled={currentPage <= 1}
              onClick={() => setRequestedPage((page) => Math.max(1, page - 1))}
            >Previous</button>
            <span>Page {currentPage} of {pageCount}</span>
            <button
              className="button-secondary"
              disabled={currentPage >= pageCount}
              onClick={() => setRequestedPage((page) => Math.min(pageCount, page + 1))}
            >Next</button>
          </div>
        </div>
      )}
    </>
  )
}

function RecommendationWorkspace({
  role,
  refreshKey,
  onNotice,
  onError,
  onChanged,
}: {
  role: DemoRole
  refreshKey: number
  onNotice: (message: string) => void
  onError: (message: string) => void
  onChanged: () => void
}) {
  const [items, setItems] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [reasons, setReasons] = useState<Record<number, string>>({})
  const [filter, setFilter] = useState('all')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await campusPulseApi.getRecommendations())
      onError('')
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Could not load recommendations.')
    } finally {
      setLoading(false)
    }
  }, [onError])

  useEffect(() => {
    void load()
  }, [load, role, refreshKey])

  async function review(item: Recommendation, decision: 'approved' | 'declined') {
    const reason = reasons[item.id]?.trim() ?? ''

    if (decision === 'declined' && !reason) {
      onError('Enter a reason before declining a recommendation.')
      return
    }

    setBusyId(item.id)
    onError('')

    try {
      await campusPulseApi.reviewRecommendation(
        item.id,
        decision,
        reason || undefined,
      )
      onNotice(`Recommendation #${item.id} ${decision}.`)
      await load()
      onChanged()
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Recommendation review failed.')
    } finally {
      setBusyId(null)
    }
  }

  const visible = items.filter(
    (item) => filter === 'all' || item.status === filter,
  )
  const pendingCount = items.filter((item) => item.status === 'pending').length

  return (
    <section className="panel fast-panel">
      <div className="panel-heading">
        <div>
          <h2>Recommendation review</h2>
          <p>Inspect each rationale and record a decision through the backend.</p>
        </div>
        <button className="button-secondary" onClick={() => void load()}>
          <RefreshCw size={15} /> Reload
        </button>
      </div>

      <section className="metric-grid">
        <Metric
          label="Visible recommendations"
          value={String(items.length)}
          caption="Returned for this role"
          icon={<ClipboardCheck size={19} />}
        />
        <Metric
          label="Pending review"
          value={String(pendingCount)}
          caption="Check each rationale"
          icon={<Clock3 size={19} />}
        />
        <Metric
          label="Current role"
          value={role.toUpperCase()}
          caption="Role-filtered results"
          icon={<ShieldCheck size={19} />}
        />
      </section>

      <div className="fast-toolbar">
        <label>
          Filter status
          <select value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="declined">Declined</option>
          </select>
        </label>
      </div>

      {loading && <p className="fast-muted">Loading recommendations…</p>}

      {!loading && visible.length === 0 && (
        <div className="fast-empty">
          No recommendations match this filter for the current role.
        </div>
      )}

      <div className="fast-workspace-list">
        {visible.map((item) => (
          <article className="fast-workspace-card" key={item.id}>
            <div className="fast-workspace-top">
              <div>
                <span className="fast-chip">
                  #{item.id} · {item.priority}
                </span>
                <h3>{item.intervention_type.replaceAll('_', ' ')}</h3>
                <p className="fast-muted">
                  {item.student_name} · {item.student_code}
                </p>
              </div>
              <span className={`fast-status fast-status-${item.status}`}>
                {item.status.replaceAll('_', ' ')}
              </span>
            </div>

            <div className="fast-workspace-detail">
              <strong>Rationale</strong>
              <p>{item.rationale}</p>
            </div>

            <div className="fast-workspace-detail">
              <strong>Suggested next step</strong>
              <p>{item.suggested_next_step}</p>
            </div>

            <div className="fast-workspace-detail">
              <strong>Intended role</strong>
              <p>{item.intended_role}</p>
            </div>

            {item.decision_reason && (
              <p className="fast-muted">Decision reason: {item.decision_reason}</p>
            )}

            {item.status === 'pending' && (
              <div className="fast-workspace-actions">
                <label>
                  Decision reason
                  <input
                    value={reasons[item.id] ?? ''}
                    onChange={(event) => setReasons((current) => ({
                      ...current,
                      [item.id]: event.target.value,
                    }))}
                    placeholder="Required when declining"
                  />
                </label>

                <div className="fast-button-row">
                  <button
                    className="button-primary"
                    disabled={busyId === item.id}
                    onClick={() => void review(item, 'approved')}
                  >
                    <CircleCheck size={16} />
                    {busyId === item.id ? 'Saving…' : 'Approve'}
                  </button>
                  <button
                    className="button-secondary"
                    disabled={busyId === item.id}
                    onClick={() => void review(item, 'declined')}
                  >
                    <CircleX size={16} /> Decline
                  </button>
                </div>
              </div>
            )}

            <small className="fast-muted">
              Created {new Date(item.created_at).toLocaleString()}
            </small>
          </article>
        ))}
      </div>
    </section>
  )
}

function InterventionWorkspace({
  role,
  refreshKey,
  onNotice,
  onError,
}: {
  role: DemoRole
  refreshKey: number
  onNotice: (message: string) => void
  onError: (message: string) => void
}) {
  const [items, setItems] = useState<Intervention[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [notes, setNotes] = useState<Record<number, string>>({})
  const [statuses, setStatuses] = useState<Record<number, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await campusPulseApi.getInterventions())
      onError('')
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Could not load interventions.')
    } finally {
      setLoading(false)
    }
  }, [onError])

  useEffect(() => {
    void load()
  }, [load, role, refreshKey])

  async function updateStatus(item: Intervention) {
    const status = statuses[item.id]

    if (!status || status === item.status) {
      onNotice('Choose a different status before saving.')
      return
    }

    setBusyId(item.id)
    onError('')

    try {
      await campusPulseApi.updateInterventionStatus(item.id, status)
      onNotice(`Intervention #${item.id} status updated.`)
      await load()
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Could not update intervention status.')
    } finally {
      setBusyId(null)
    }
  }

  async function addFollowUp(item: Intervention) {
    const note = notes[item.id]?.trim()

    if (!note) {
      onError('Enter a follow-up note before saving.')
      return
    }

    setBusyId(item.id)
    onError('')

    try {
      await campusPulseApi.recordFollowUp(item.id, note)
      setNotes((current) => ({ ...current, [item.id]: '' }))
      onNotice(`Follow-up recorded for intervention #${item.id}.`)
      await load()
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Could not record follow-up.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="panel fast-panel">
      <div className="panel-heading">
        <div>
          <h2>Intervention workbench</h2>
          <p>Review assignments, update status, and record follow-up notes.</p>
        </div>
        <button className="button-secondary" onClick={() => void load()}>
          <RefreshCw size={15} /> Reload
        </button>
      </div>

      <section className="metric-grid">
        <Metric
          label="Visible interventions"
          value={String(items.length)}
          caption="Returned for this role"
          icon={<CalendarClock size={19} />}
        />
        <Metric
          label="Open interventions"
          value={String(items.filter((item) =>
            !['completed', 'cancelled', 'closed'].includes(item.status.toLowerCase()),
          ).length)}
          caption="Not marked as closed"
          icon={<Clock3 size={19} />}
        />
        <Metric
          label="Current role"
          value={role.toUpperCase()}
          caption="Role-filtered results"
          icon={<ShieldCheck size={19} />}
        />
      </section>

      {loading && <p className="fast-muted">Loading interventions…</p>}

      {!loading && items.length === 0 && (
        <div className="fast-empty">
          No interventions are available for the current role.
        </div>
      )}

      <div className="fast-workspace-list">
        {items.map((item) => (
          <article className="fast-workspace-card" key={item.id}>
            <div className="fast-workspace-top">
              <div>
                <span className="fast-chip">
                  #{item.id} · {item.priority}
                </span>
                <h3>{item.intervention_type.replaceAll('_', ' ')}</h3>
                <p className="fast-muted">
                  {item.student_name} · {item.student_code}
                </p>
              </div>
              <span className={`fast-status fast-status-${item.status}`}>
                {item.status.replaceAll('_', ' ')}
              </span>
            </div>

            <div className="fast-workspace-detail">
              <strong>Description</strong>
              <p>{item.description}</p>
            </div>

            <div className="fast-workspace-detail">
              <strong>Assignment</strong>
              <p>
                Owner: {item.assigned_owner || 'Not specified'} · Role: {item.assigned_role}
              </p>
              {item.supporting_role && <p>Supporting role: {item.supporting_role}</p>}
              <p>Due: {new Date(item.due_date).toLocaleDateString()}</p>
            </div>

            {!['completed', 'cancelled', 'closed'].includes(item.status.toLowerCase()) && (
              <>
                <div className="fast-workspace-actions">
                  <label>
                    Update status
                    <select
                      value={statuses[item.id] ?? item.status}
                      onChange={(event) => setStatuses((current) => ({
                        ...current,
                        [item.id]: event.target.value,
                      }))}
                    >
                      <option value={item.status}>{item.status.replaceAll('_', ' ')} (current)</option>
                      <option value="assigned">Assigned</option>
                      <option value="in_progress">In progress</option>
                      <option value="follow_up">Follow-up</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                  </label>
                  <div className="fast-button-row">
                    <button
                      className="button-primary"
                      disabled={busyId === item.id}
                      onClick={() => void updateStatus(item)}
                    >
                      {busyId === item.id ? 'Saving…' : 'Save status'}
                    </button>
                  </div>
                </div>

                <div className="fast-workspace-actions">
                  <label>
                    Follow-up note
                    <textarea
                      value={notes[item.id] ?? ''}
                      onChange={(event) => setNotes((current) => ({
                        ...current,
                        [item.id]: event.target.value,
                      }))}
                      placeholder="Record the action taken, response, or next step…"
                      rows={3}
                    />
                  </label>
                  <div className="fast-button-row">
                    <button
                      className="button-secondary"
                      disabled={busyId === item.id}
                      onClick={() => void addFollowUp(item)}
                    >
                      {busyId === item.id ? 'Saving…' : 'Record follow-up'}
                    </button>
                  </div>
                </div>
              </>
            )}

            <small className="fast-muted">
              Updated {new Date(item.updated_at).toLocaleString()}
            </small>
          </article>
        ))}
      </div>
    </section>
  )
}

export default App



function AssessmentReport({ data }: { data: Record<string, unknown> }) {
  const titleize = (key: string) =>
    key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

  const displayValue = (value: unknown): string => {
    if (value === null || value === undefined || value === '') return 'Not provided'
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    if (typeof value === 'string' || typeof value === 'number') return String(value)
    return ''
  }

  const renderValue = (value: unknown, key: string): React.ReactNode => {
    if (value === null || value === undefined || value === '') {
      return <span className="assessment-empty">Not provided</span>
    }

    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="assessment-empty">None recorded</span>

      return (
        <div className="assessment-list">
          {value.map((item, index) => (
            <div className="assessment-list-item" key={`${key}-${index}`}>
              {typeof item === 'object' && item !== null
                ? renderObject(item as Record<string, unknown>, `${key}-${index}`)
                : displayValue(item)}
            </div>
          ))}
        </div>
      )
    }

    if (typeof value === 'object') {
      return renderObject(value as Record<string, unknown>, key)
    }

    return <span>{displayValue(value)}</span>
  }

  const renderObject = (object: Record<string, unknown>, prefix: string) => {
    const entries = Object.entries(object).filter(([, value]) => value !== undefined)

    if (!entries.length) return <span className="assessment-empty">No details provided</span>

    return (
      <div className="assessment-details">
        {entries.map(([key, value]) => (
          <div className="assessment-detail" key={`${prefix}-${key}`}>
            <span className="assessment-detail-label">{titleize(key)}</span>
            <div className="assessment-detail-value">{renderValue(value, key)}</div>
          </div>
        ))}
      </div>
    )
  }

  const summaryEntries = Object.entries(data).filter(
    ([, value]) => value !== null && typeof value !== 'object',
  )
  const detailEntries = Object.entries(data).filter(
    ([, value]) => value !== null && typeof value === 'object',
  )

  return (
    <section className="assessment-report" aria-live="polite">
      <div className="assessment-report-header">
        <div>
          <span className="assessment-report-kicker">ASSESSMENT REPORT</span>
          <h3>Academic support findings</h3>
          <p>Backend-generated results for staff review. Confirm the evidence before taking action.</p>
        </div>
        <span className="assessment-report-status">Completed</span>
      </div>

      {summaryEntries.length > 0 && (
        <div className="assessment-summary-grid">
          {summaryEntries.map(([key, value]) => (
            <div className="assessment-summary-card" key={key}>
              <span>{titleize(key)}</span>
              <strong>{displayValue(value)}</strong>
            </div>
          ))}
        </div>
      )}

      {detailEntries.map(([key, value]) => (
        <section className="assessment-section" key={key}>
          <h4>{titleize(key)}</h4>
          {renderValue(value, key)}
        </section>
      ))}

      <div className="assessment-review-note">
        <strong>Staff review required</strong>
        <p>These findings support human decision-making; they should not be treated as an automatic diagnosis or final decision.</p>
      </div>
    </section>
  )
}
