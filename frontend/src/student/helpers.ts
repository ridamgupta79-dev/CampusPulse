export function formatUtcDateTime(iso: string | null | undefined): string {
  if (!iso) return 'Not available'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  })
}

export function formatUtcDate(iso: string | null | undefined): string {
  if (!iso) return 'Not available'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

export function hoursUntil(iso: string): number {
  return (new Date(iso).getTime() - Date.now()) / 3_600_000
}

export function dueLabel(iso: string): string {
  const hours = hoursUntil(iso)
  if (hours < -1) return `Due ${formatUtcDateTime(iso)} (UTC) — past due`
  if (hours < 0) return `Due ${formatUtcDateTime(iso)} (UTC) — closing now`
  if (hours < 48) {
    const h = Math.max(1, Math.floor(hours))
    return `Due in ${h} hour${h === 1 ? '' : 's'} (${formatUtcDate(iso)} UTC)`
  }
  return `Due ${formatUtcDateTime(iso)} (UTC)`
}

export const SUBMISSION_STATE_LABELS: Record<string, string> = {
  not_submitted: 'Not submitted',
  draft: 'Draft saved',
  submitted: 'Awaiting grading',
  submitted_late: 'Submitted late',
  graded: 'Graded',
  returned: 'Returned for revision',
  closed: 'Closed',
}

export const SUPPORT_TYPE_LABELS: Record<string, string> = {
  academic_checkin: 'Academic check-in',
  mentor_support: 'Mentor support',
  assignment_clarification: 'Assignment clarification',
}
