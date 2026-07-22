import { useEffect, useState } from 'react'
import type { StatsSummary } from '../api/types'
import { fetchStatsSummary } from '../api/dashboardApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { Card } from '../components/ui'
import { ErrorState, LoadingState } from '../components/UiStates'
import { useAuthStore } from '../store/authStore'

function statusTone(pct: number): string {
  if (pct >= 90) return 'text-emerald-600 dark:text-emerald-400'
  if (pct >= 70) return 'text-amber-600 dark:text-amber-400'
  return 'text-rose-600 dark:text-rose-400'
}

export function CustomerHomePage() {
  const user = useAuthStore((s) => s.user)
  const [stats, setStats] = useState<StatsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await fetchStatsSummary()
        if (!cancelled) setStats(data)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError || err instanceof Error ? err.message : 'Şebeke durumu alınamadı')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  const activeIncidents = stats ? stats.by_priority.reduce((sum, p) => sum + p.count, 0) : 0

  return (
    <AppShell title="NetOpsCell — Müşteri" subtitle="Şebeke durumu">
      <Card className="mb-6 flex flex-col items-center gap-2 p-8 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-tc-yellow-100 text-2xl dark:bg-tc-yellow-500/15">
          📶
        </span>
        <h1 className="text-2xl font-bold">Hoş geldiniz{user?.first_name ? `, ${user.first_name}` : ''}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Turkcell şebeke sağlığını buradan takip edebilirsiniz. Kişiye özel arıza takibi (kaydettiğiniz
          hattınıza bağlı) yakında eklenecek.
        </p>
      </Card>

      {loading && <LoadingState message="Şebeke durumu yükleniyor…" />}
      {error && <ErrorState message={error} />}

      {!loading && !error && stats && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="p-5 text-center">
            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Aktif arıza</p>
            <p className="mt-1 text-3xl font-bold text-tc-navy-900 dark:text-slate-100">{activeIncidents}</p>
          </Card>
          <Card className="p-5 text-center">
            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">SLA uyum oranı</p>
            <p className={`mt-1 text-3xl font-bold ${statusTone(stats.sla_compliance_pct)}`}>
              %{stats.sla_compliance_pct.toFixed(0)}
            </p>
          </Card>
          <Card className="p-5 text-center">
            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
              SLA aşan aktif arıza
            </p>
            <p className="mt-1 text-3xl font-bold text-rose-600 dark:text-rose-400">{stats.sla_breached_active}</p>
          </Card>
        </div>
      )}
    </AppShell>
  )
}
