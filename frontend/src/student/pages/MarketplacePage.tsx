import { useCallback, useEffect, useState } from 'react'
import { Gift, Medal, ShoppingBag } from 'lucide-react'
import {
  studentApi,
  type LeaderboardData,
  type RedeemResult,
  type RedemptionRecord,
  type RewardItem,
  type RewardsData,
} from '../studentApi'
import {
  SpAlert,
  SpEmpty,
  SpSection,
} from '../ui'
import { formatUtcDateTime } from '../helpers'

type Tab = 'rewards' | 'leaderboard' | 'history'

export default function MarketplacePage({ refreshKey }: { refreshKey: number }) {
  const [tab, setTab] = useState<Tab>('rewards')
  const [rewards, setRewards] = useState<RewardsData | null>(null)
  const [board, setBoard] = useState<LeaderboardData | null>(null)
  const [boardPage, setBoardPage] = useState(1)
  const [history, setHistory] = useState<RedemptionRecord[] | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [redeemed, setRedeemed] = useState<RedeemResult | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const loadRewards = useCallback(() => {
    studentApi
      .rewards()
      .then((result) => setRewards(result))
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load the marketplace.')
      })
  }, [])

  const loadBoard = useCallback((page: number) => {
    studentApi
      .leaderboard(null, page)
      .then((result) => {
        setBoard(result)
        setError('')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load the leaderboard.')
      })
  }, [])

  const loadHistory = useCallback(() => {
    studentApi
      .redemptions()
      .then((result) => setHistory(result))
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load your redemptions.')
      })
  }, [])

  useEffect(() => {
    void loadRewards()
  }, [loadRewards, refreshKey])

  useEffect(() => {
    if (tab === 'leaderboard') void loadBoard(boardPage)
  }, [tab, boardPage, loadBoard, refreshKey])

  useEffect(() => {
    if (tab === 'history') void loadHistory()
  }, [tab, loadHistory, refreshKey])

  async function redeem(reward: RewardItem) {
    setBusyId(reward.id)
    setError('')
    setNotice('')
    try {
      const result = await studentApi.redeem(reward.id)
      setRedeemed(result)
      setNotice(
        `Redeemed "${result.reward.name}". Reference ${result.reference}. Balance is now ${result.balance_after}.`,
      )
      loadRewards()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Redemption failed.')
    } finally {
      setBusyId(null)
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

      <div className="sp-filter-row" role="tablist" aria-label="Marketplace sections">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'rewards'}
          className={`sp-filter ${tab === 'rewards' ? 'sp-filter-active' : ''}`}
          onClick={() => setTab('rewards')}
        >
          <Gift size={15} /> Rewards
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'leaderboard'}
          className={`sp-filter ${tab === 'leaderboard' ? 'sp-filter-active' : ''}`}
          onClick={() => setTab('leaderboard')}
        >
          <Medal size={15} /> Leaderboard
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'history'}
          className={`sp-filter ${tab === 'history' ? 'sp-filter-active' : ''}`}
          onClick={() => setTab('history')}
        >
          <ShoppingBag size={15} /> My redemptions
        </button>
      </div>

      {tab === 'rewards' && (
        <>
          {redeemed && (
            <SpSection
              title="Redemption confirmed"
              subtitle="This is a demonstration environment — vouchers are simulated."
            >
              <div className="sp-redemption-receipt">
                <strong>{redeemed.reward.name}</strong>
                <span>Reference: {redeemed.reference}</span>
                <span>Points deducted: {redeemed.reward.cost}</span>
                <span>New balance: {redeemed.balance_after}</span>
              </div>
            </SpSection>
          )}
          {!rewards ? (
            <div className="sp-loading">Loading rewards…</div>
          ) : (
            <SpSection
              title={`Rewards — balance ${rewards.balance} points`}
              subtitle="Rewards and prices are set by your institution. Simulated vouchers are clearly labelled and hold no real-world value."
            >
              {rewards.rewards.length === 0 ? (
                <SpEmpty title="No rewards available right now." />
              ) : (
                <ul className="sp-reward-grid">
                  {rewards.rewards.map((reward) => (
                    <li key={reward.id} className="sp-reward-card">
                      <div className="sp-reward-head">
                        <strong>{reward.name}</strong>
                        <span className="sp-badge sp-badge-blue">
                          {reward.cost} pts
                        </span>
                      </div>
                      <p>{reward.description}</p>
                      {reward.reward_type === 'simulated' && (
                        <span className="sp-chip sp-chip-lavender">
                          Simulated — demo only
                        </span>
                      )}
                      <div className="sp-reward-foot">
                        {reward.already_redeemed ? (
                          <span className="sp-reward-state">Already redeemed</span>
                        ) : reward.affordable ? (
                          <button
                            type="button"
                            className="sp-button-primary"
                            disabled={busyId === reward.id || reward.stock === 0}
                            onClick={() => void redeem(reward)}
                          >
                            {busyId === reward.id
                              ? 'Redeeming…'
                              : 'Redeem now'}
                          </button>
                        ) : (
                          <span className="sp-reward-state">
                            {reward.points_needed} more points needed
                          </span>
                        )}
                        <span className="sp-list-meta">
                          {reward.stock === null
                            ? 'Unlimited stock'
                            : `${reward.stock} left`}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </SpSection>
          )}
        </>
      )}

      {tab === 'leaderboard' &&
        (!board ? (
          <div className="sp-loading">Loading leaderboard…</div>
        ) : (
          <SpSection
            title="Pulse Points leaderboard"
            subtitle={board.metric_note}
            actions={
              board.total > board.page_size ? (
                <div className="sp-pagination">
                  <button
                    type="button"
                    className="sp-button-secondary"
                    disabled={board.page <= 1}
                    onClick={() => setBoardPage((page) => page - 1)}
                  >
                    Previous
                  </button>
                  <span>
                    Page {board.page} of {Math.ceil(board.total / board.page_size)}
                  </span>
                  <button
                    type="button"
                    className="sp-button-secondary"
                    disabled={board.page * board.page_size >= board.total}
                    onClick={() => setBoardPage((page) => page + 1)}
                  >
                    Next
                  </button>
                </div>
              ) : undefined
            }
          >
            {board.entries.length === 0 ? (
              <SpEmpty
                title="No ranked students yet."
                hint="The leaderboard fills in as graded assignments award points."
              />
            ) : (
              <div className="sp-table-wrap">
                <table className="sp-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Student</th>
                      <th>Cohort</th>
                      <th>Net earned</th>
                    </tr>
                  </thead>
                  <tbody>
                    {board.entries.map((entry) => (
                      <tr
                        key={entry.student_id}
                        className={entry.is_current_student ? 'sp-row-me' : ''}
                      >
                        <td>#{entry.rank}</td>
                        <td>
                          <strong>{entry.display_name}</strong>
                          {entry.is_current_student && (
                            <span className="sp-chip sp-chip-mint">You</span>
                          )}
                        </td>
                        <td>{entry.cohort}</td>
                        <td>{entry.net_earned}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="sp-form-hint">
              {board.me.rank === null
                ? 'Earn your first points to appear on the leaderboard.'
                : `Your position: #${board.me.rank} with ${board.me.net_earned} net earned points.`}
              {' '}Only names, cohorts, and ranks are shown — never emails or student codes.
            </p>
          </SpSection>
        ))}

      {tab === 'history' &&
        (!history ? (
          <div className="sp-loading">Loading your redemptions…</div>
        ) : (
          <SpSection
            title="My redemptions"
            subtitle="Keep the reference in case you need to collect a reward."
          >
            {history.length === 0 ? (
              <SpEmpty
                title="No redemptions yet."
                hint="Redeemed rewards and their references appear here."
              />
            ) : (
              <div className="sp-table-wrap">
                <table className="sp-table">
                  <thead>
                    <tr>
                      <th>Date (UTC)</th>
                      <th>Reward</th>
                      <th>Cost</th>
                      <th>Reference</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((record) => (
                      <tr key={record.id}>
                        <td>{formatUtcDateTime(record.created_at)}</td>
                        <td>{record.reward_name ?? 'Not available'}</td>
                        <td>{record.cost}</td>
                        <td>{record.reference}</td>
                        <td>
                          <span className={`sp-badge sp-badge-${record.status === 'completed' ? 'mint' : 'blue'}`}>
                            {record.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SpSection>
        ))}
    </>
  )
}
