import { useCallback, useEffect, useState } from 'react'
import { studentApi, type LedgerEntry, type PulseBalance } from '../studentApi'
import { formatUtcDateTime } from '../helpers'
import { SpAlert, SpEmpty, SpSection, SpStat } from '../ui'

const TXN_LABELS: Record<string, string> = {
  award: 'Award',
  redemption: 'Redemption',
  refund: 'Refund',
  adjustment: 'Adjustment',
  reversal: 'Reversal',
}

const TYPES = [
  { id: 'all', label: 'All transactions' },
  { id: 'earned', label: 'Earned' },
  { id: 'redeemed', label: 'Redeemed' },
  { id: 'adjusted', label: 'Adjustments' },
] as const

export default function PulsePointsPage({ refreshKey }: { refreshKey: number }) {
  const [balance, setBalance] = useState<PulseBalance | null>(null)
  const [type, setType] = useState<string>('all')
  const [entries, setEntries] = useState<LedgerEntry[] | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    Promise.all([studentApi.pulseBalance(), studentApi.ledger(type)])
      .then(([balanceResult, ledgerResult]) => {
        setBalance(balanceResult)
        setEntries(ledgerResult)
        setError('')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load Pulse Points.')
      })
  }, [type])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  if (error) return <SpAlert tone="error">{error}</SpAlert>
  if (!balance || entries === null) {
    return <div className="sp-loading">Loading Pulse Points…</div>
  }

  return (
    <>
      <div className="sp-stat-grid">
        <SpStat
          label="Current balance"
          value={String(balance.balance)}
          caption="Spendable in the Pulse Marketplace"
          tone="mint"
        />
        <SpStat
          label="Lifetime earned"
          value={String(balance.lifetime_earned)}
          caption="Net of adjustments and reversals"
          tone="blue"
        />
        <SpStat
          label="Lifetime redeemed"
          value={String(balance.lifetime_redeemed)}
          caption="Total spent on rewards"
          tone="lavender"
        />
        <SpStat
          label="Awaiting quality review"
          value={String(balance.pending_quality_reviews)}
          caption="Submissions waiting for teacher grading"
          tone="blue"
        />
      </div>

      <SpSection
        title="How Pulse Points work"
        subtitle="Your balance comes from a server-side ledger — the same source the leaderboard and marketplace use."
      >
        <ul className="sp-note-list">
          <li>Timing points (0–4) are computed from when you submit relative to the publish and deadline times.</li>
          <li>Quality points (0–3) are awarded only by your teacher during grading.</li>
          <li>A submission earns at most 7 points; late submissions never receive the on-time timing bonus.</li>
          <li>Points appear only after the teacher grades and releases your work; corrections appear as separate adjustment entries.</li>
        </ul>
      </SpSection>

      <SpSection
        title="Transaction ledger"
        subtitle="Immutable history. Every award, redemption, and correction is recorded here."
        actions={
          <select
            value={type}
            onChange={(event) => setType(event.target.value)}
            aria-label="Filter ledger by type"
          >
            {TYPES.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.label}
              </option>
            ))}
          </select>
        }
      >
        {entries.length === 0 ? (
          <SpEmpty
            title="No transactions yet."
            hint="Submit an assignment and have it graded to earn your first points."
          />
        ) : (
          <div className="sp-table-wrap">
            <table className="sp-table">
              <thead>
                <tr>
                  <th>Date (UTC)</th>
                  <th>Type</th>
                  <th>Points</th>
                  <th>Timing / Quality</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{formatUtcDateTime(entry.created_at)}</td>
                    <td>
                      <span className={`sp-badge sp-badge-${entry.txn_type === 'award' ? 'mint' : entry.txn_type === 'redemption' ? 'lavender' : 'blue'}`}>
                        {TXN_LABELS[entry.txn_type] ?? entry.txn_type}
                      </span>
                    </td>
                    <td className={entry.amount >= 0 ? 'sp-amount-plus' : 'sp-amount-minus'}>
                      {entry.amount >= 0 ? `+${entry.amount}` : entry.amount}
                    </td>
                    <td>
                      {entry.timing_points === null && entry.quality_points === null
                        ? '—'
                        : `${entry.timing_points ?? 0} / ${entry.quality_points ?? 0}`}
                    </td>
                    <td>
                      {entry.assignment_title
                        ? `${entry.assignment_title} — ${entry.reason}`
                        : entry.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SpSection>
    </>
  )
}
