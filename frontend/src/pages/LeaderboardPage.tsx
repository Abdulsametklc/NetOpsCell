import { useEffect, useState } from 'react'
import type { LeaderboardEntry, LeaderboardPeriod } from '../api/types'
import { fetchLeaderboard, gameModeLabel } from '../api/gameApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'

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

  return (
    <AppShell title="NetOpsCell — Liderlik" subtitle={gameModeLabel()}>
      <div className="mb-4 flex gap-2">
        {(['daily', 'weekly'] as const).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPeriod(p)}
            className={`rounded px-3 py-1.5 text-sm ${
              period === p ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-300'
            }`}
          >
            {p === 'daily' ? 'Günlük' : 'Haftalık'}
          </button>
        ))}
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && rows.length === 0 && (
        <EmptyState message="Bu dönemde henüz puan kaydı yok." />
      )}
      {!loading && !error && rows.length > 0 && (
        <ol className="space-y-2">
          {rows.map((r) => (
            <li
              key={r.user_id}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <span className="w-8 text-center font-mono text-slate-500">#{r.rank ?? '—'}</span>
                <div>
                  <p className="font-medium">{r.display_name ?? r.user_id}</p>
                  {r.level && <p className="text-xs text-slate-500">{r.level}</p>}
                </div>
              </div>
              <span className="font-mono text-sky-300">{r.points} puan</span>
            </li>
          ))}
        </ol>
      )}
    </AppShell>
  )
}
