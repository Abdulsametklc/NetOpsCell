import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type {
  AccuracyReport,
  AssignableTeam,
  StatsSummary,
  UnassignedIncident,
} from '../api/types'
import {
  assignIncident,
  dashboardModeLabel,
  fetchAccuracy,
  fetchAssignableTeams,
  fetchStatsSummary,
  fetchUnassignedQueue,
} from '../api/dashboardApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
import { useToastStore } from '../store/toastStore'

const PIE_COLORS = ['#38bdf8', '#fbbf24', '#f97316', '#f43f5e', '#a78bfa', '#94a3b8']

function ChartCard({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-300">{title}</h3>
      <div className="h-56 w-full min-w-0">{children}</div>
    </section>
  )
}

export function SupervisorDashboardPage() {
  const pushToast = useToastStore((s) => s.push)
  const [stats, setStats] = useState<StatsSummary | null>(null)
  const [accuracy, setAccuracy] = useState<AccuracyReport | null>(null)
  const [queue, setQueue] = useState<UnassignedIncident[]>([])
  const [teams, setTeams] = useState<AssignableTeam[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assignFor, setAssignFor] = useState<string | null>(null)
  const [teamId, setTeamId] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [s, a, q, t] = await Promise.all([
        fetchStatsSummary(),
        fetchAccuracy(),
        fetchUnassignedQueue(),
        fetchAssignableTeams(),
      ])
      setStats(s)
      setAccuracy(a)
      setQueue(q)
      setTeams(t)
      if (t[0]) setTeamId(t[0].team_id)
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Dashboard yüklenemedi')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function onAssign() {
    if (!assignFor || !teamId) return
    setBusy(true)
    try {
      await assignIncident(assignFor, teamId)
      setQueue((prev) => prev.filter((i) => i.id !== assignFor))
      setAssignFor(null)
      pushToast('success', 'Atama yapıldı', `Ekip ${teamId}`)
    } catch (err) {
      pushToast(
        'warning',
        'Atama başarısız',
        err instanceof Error ? err.message : 'Hata',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell title="NetOpsCell — Süpervizör" subtitle={dashboardModeLabel()}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-medium">Operasyon özeti</h2>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900"
        >
          Yenile
        </button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}

      {!loading && !error && stats && accuracy && (
        <div className="grid gap-4 md:grid-cols-2">
          <ChartCard title="1. Arıza dağılımı (tür)">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stats.by_fault_type}
                  dataKey="count"
                  nameKey="name"
                  outerRadius={70}
                  label
                >
                  {stats.by_fault_type.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="2. Öncelik dağılımı">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.by_priority}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" fill="#38bdf8" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="2b. Öncelik trendi (7 gün)">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.priority_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="KRITIK" stroke="#f43f5e" strokeWidth={2} />
                <Line type="monotone" dataKey="YUKSEK" stroke="#f97316" strokeWidth={2} />
                <Line type="monotone" dataKey="ORTA" stroke="#fbbf24" strokeWidth={2} />
                <Line type="monotone" dataKey="DUSUK" stroke="#94a3b8" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
            <h3 className="mb-3 text-sm font-medium text-slate-300">3. SLA uyum</h3>
            <p className="text-3xl font-semibold text-emerald-300">
              %{stats.sla_compliance_pct.toFixed(1)}
            </p>
            <p className="mt-2 text-sm text-rose-300">
              Aktif SLA aşımı: {stats.sla_breached_active}
            </p>
          </section>

          <ChartCard title="4. AI doğruluk (kategori)">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={accuracy.by_category} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" domain={[0, 100]} stroke="#94a3b8" fontSize={11} />
                <YAxis type="category" dataKey="category" width={90} stroke="#94a3b8" fontSize={10} />
                <Tooltip />
                <Bar dataKey="pct" fill="#a78bfa" name="Doğruluk %" />
              </BarChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-slate-500">
              Genel %{accuracy.overall_pct} · False alarm: {accuracy.false_alarms}
            </p>
          </ChartCard>

          <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 md:col-span-2">
            <h3 className="mb-3 text-sm font-medium text-slate-300">5. Saha ekibi performansı</h3>
            {stats.teams.length === 0 ? (
              <EmptyState message="Ekip verisi yok." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500">
                    <tr>
                      <th className="py-2 pr-3">Ekip</th>
                      <th className="py-2 pr-3">Çözülen</th>
                      <th className="py-2 pr-3">Ort. dk</th>
                      <th className="py-2">Tekrar oranı</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.teams.map((t) => (
                      <tr key={t.team_id} className="border-t border-slate-800">
                        <td className="py-2 pr-3">{t.team_name}</td>
                        <td className="py-2 pr-3 font-mono">{t.resolved}</td>
                        <td className="py-2 pr-3 font-mono">{t.avg_minutes}</td>
                        <td className="py-2 font-mono">
                          %{(t.reopen_rate * 100).toFixed(0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 md:col-span-2">
            <h3 className="mb-3 text-sm font-medium text-slate-300">
              6. Bekleyen atama kuyruğu
            </h3>
            {queue.length === 0 ? (
              <EmptyState message="Kuyruk boş." />
            ) : (
              <ul className="space-y-3">
                {queue.map((item) => (
                  <li
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded border border-slate-800 bg-slate-950/50 px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-mono text-sky-300">{item.incident_number}</p>
                      <p className="text-slate-400">
                        {item.station_code} · {item.fault_type ?? '—'} · {item.priority ?? '—'}
                      </p>
                    </div>
                    {assignFor === item.id ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <select
                          className="rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs"
                          value={teamId}
                          onChange={(e) => setTeamId(e.target.value)}
                        >
                          {teams.map((t) => (
                            <option key={t.team_id} value={t.team_id}>
                              {t.team_name} (yük {t.active_load})
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void onAssign()}
                          className="rounded bg-emerald-700 px-3 py-1.5 text-xs disabled:opacity-60"
                        >
                          Onayla
                        </button>
                        <button
                          type="button"
                          className="rounded border border-slate-700 px-3 py-1.5 text-xs"
                          onClick={() => setAssignFor(null)}
                        >
                          İptal
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="rounded bg-sky-700 px-3 py-1.5 text-xs hover:bg-sky-600"
                        onClick={() => setAssignFor(item.id)}
                      >
                        Manuel ata
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </AppShell>
  )
}
