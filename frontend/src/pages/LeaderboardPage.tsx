import { useEffect, useState } from 'react'
import type { LeaderboardEntry, LeaderboardPeriod } from '../api/types'
import { fetchLeaderboard } from '../api/gameApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
import { Card, Pill } from '../components/ui'

export function LeaderboardPage() {
  const [period, setPeriod] = useState<LeaderboardPeriod>('daily')
  const [rows, setRows] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchLeaderboard(period)
        if (!cancelled) setRows(data)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError || err instanceof Error ? err.message : 'Liste alınamadı')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [period])

  const medal = (rank: number | undefined) => {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return null
  }

  return (
    <AppShell title="NetOpsCell — Liderlik">
      <div className="mb-4 flex gap-2">
        {(['daily', 'weekly'] as const).map((p) => (
          <Pill key={p} active={period === p} onClick={() => setPeriod(p)}>
            {p === 'daily' ? 'Günlük' : 'Haftalık'}
          </Pill>
        ))}
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && rows.length === 0 && <EmptyState message="Bu dönemde henüz puan kaydı yok." />}
      {!loading && !error && rows.length > 0 && (
        <ol className="space-y-2">
          {rows.map((r) => (
            <Card key={r.user_id} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="flex w-8 items-center justify-center text-center font-mono text-slate-400 dark:text-slate-500">
                  {medal(r.rank) ?? `#${r.rank ?? '—'}`}
                </span>
                <div>
                  <p className="font-medium text-tc-navy-950 dark:text-slate-100">{r.display_name ?? r.user_id}</p>
                  {r.level && <p className="text-xs text-slate-500 dark:text-slate-400">{r.level}</p>}
                </div>
              </div>
              <span className="font-mono font-semibold text-tc-navy-800 dark:text-tc-yellow-400">
                {r.points} puan
              </span>
            </Card>
          ))}
        </ol>
      )}
    </AppShell>
  )
}
