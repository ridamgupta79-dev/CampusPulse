import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { SUBMISSION_STATE_LABELS } from './helpers'

export function SpAlert({
  tone,
  children,
  onDismiss,
}: {
  tone: 'success' | 'error' | 'info'
  children: ReactNode
  onDismiss?: () => void
}) {
  const Icon =
    tone === 'success' ? CheckCircle2 : tone === 'error' ? AlertTriangle : Info
  return (
    <div className={`sp-alert sp-alert-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon size={18} />
      <span>{children}</span>
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss message">
          <XSmall />
        </button>
      )}
    </div>
  )
}

function XSmall() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  )
}

export function SpEmpty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="sp-empty">
      <strong>{title}</strong>
      {hint && <span>{hint}</span>}
    </div>
  )
}

export function SpStat({
  label,
  value,
  caption,
  tone = 'blue',
}: {
  label: string
  value: string
  caption?: string
  tone?: 'blue' | 'mint' | 'lavender'
}) {
  return (
    <div className={`sp-stat sp-stat-${tone}`}>
      <span className="sp-stat-label">{label}</span>
      <strong className="sp-stat-value">{value}</strong>
      {caption && <span className="sp-stat-caption">{caption}</span>}
    </div>
  )
}

export function SpSection({
  title,
  subtitle,
  children,
  actions,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
}) {
  return (
    <section className="sp-panel">
      <div className="sp-panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

export function StateBadge({ state }: { state: string }) {
  const tone =
    state === 'graded'
      ? 'mint'
      : state === 'submitted' || state === 'submitted_late'
        ? 'blue'
        : state === 'returned'
          ? 'lavender'
          : 'neutral'
  return (
    <span className={`sp-badge sp-badge-${tone}`}>
      {SUBMISSION_STATE_LABELS[state] ?? state}
    </span>
  )
}
