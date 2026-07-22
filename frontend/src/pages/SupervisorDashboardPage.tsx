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
import type { AccuracyReport, AssignableTeam, StatsSummary, UnassignedIncident } from '../api/types'
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
import { Button, Card, Select } from '../components/ui'
import { useTheme } from '../lib/theme'
import { useToastStore } from '../store/toastStore'

// Turkcell marka paleti: sarı öne çıkan seri, lacivert + tamamlayıcı tonlar destekte.
const PIE_COLORS = ['#ffc800', '#4d76b8', '#f97316', '#f43f5e', '#a78bfa', '#5b7ba8']

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">{title}</h3>
      <div className="h-56 w-full min-w-0">{children}</div>
    </Card>
  )
}

export function SupervisorDashboardPage() {
  const pushToast = useToastStore((s) => s.push)
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const gridStroke = isDark ? '#152c5c' : '#e2e8f0'
  const axisStroke = isDark ? '#94a3b8' : '#64748b'

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
      pushToast('warning', 'Atama başarısız', err instanceof Error ? err.message : 'Hata')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell title="NetOpsCell — Süpervizör" subtitle={dashboardModeLabel()}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">Operasyon özeti</h2>
        <Button variant="secondary" size="sm" onClick={() => void load()}>
          Yenile
        </Button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}

      {!loading && !error && stats && accuracy && (
        <div className="grid gap-4 md:grid-cols-2">
          <ChartCard title="1. Arıza dağılımı (tür)">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={stats.by_fault_type} dataKey="count" nameKey="name" outerRadius={70} label>
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
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="name" stroke={axisStroke} fontSize={11} />
                <YAxis stroke={axisStroke} fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" fill="#ffc800" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="2b. Öncelik trendi (7 gün)">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.priority_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="day" stroke={axisStroke} fontSize={11} />
                <YAxis stroke={axisStroke} fontSize={11} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="KRITIK" stroke="#f43f5e" strokeWidth={2} />
                <Line type="monotone" dataKey="YUKSEK" stroke="#f97316" strokeWidth={2} />
                <Line type="monotone" dataKey="ORTA" stroke="#ffc800" strokeWidth={2} />
                <Line type="monotone" dataKey="DUSUK" stroke="#5b7ba8" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <Card className="p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">3. SLA uyum</h3>
            <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">
              %{stats.sla_compliance_pct.toFixed(1)}
            </p>
            <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">
              Aktif SLA aşımı: {stats.sla_breached_active}
            </p>
          </Card>

          <ChartCard title="4. AI doğruluk (kategori)">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={accuracy.by_category} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis type="number" domain={[0, 100]} stroke={axisStroke} fontSize={11} />
                <YAxis type="category" dataKey="category" width={90} stroke={axisStroke} fontSize={10} />
                <Tooltip />
                <Bar dataKey="pct" fill="#4d76b8" name="Doğruluk %" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Genel %{accuracy.overall_pct} · False alarm: {accuracy.false_alarms}
            </p>
          </ChartCard>

          <Card className="p-4 md:col-span-2">
            <h3 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">
              5. Saha ekibi performansı
            </h3>
            {stats.teams.length === 0 ? (
              <EmptyState message="Ekip verisi yok." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500 dark:text-slate-400">
                    <tr>
                      <th className="py-2 pr-3">Ekip</th>
                      <th className="py-2 pr-3">Çözülen</th>
                      <th className="py-2 pr-3">Ort. dk</th>
                      <th className="py-2">Tekrar oranı</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.teams.map((t) => (
                      <tr key={t.team_id} className="border-t border-slate-200 dark:border-tc-navy-800">
                        <td className="py-2 pr-3">{t.team_name}</td>
                        <td className="py-2 pr-3 font-mono">{t.resolved}</td>
                        <td className="py-2 pr-3 font-mono">{t.avg_minutes}</td>
                        <td className="py-2 font-mono">%{(t.reopen_rate * 100).toFixed(0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card className="p-4 md:col-span-2">
            <h3 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">
              6. Bekleyen atama kuyruğu
            </h3>
            {queue.length === 0 ? (
              <EmptyState message="Kuyruk boş." />
            ) : (
              <ul className="space-y-3">
                {queue.map((item) => (
                  <li
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-tc-navy-800 dark:bg-tc-navy-950/50"
                  >
                    <div>
                      <p className="font-mono text-tc-navy-700 dark:text-tc-yellow-400">{item.incident_number}</p>
                      <p className="text-slate-500 dark:text-slate-400">
                        {item.station_code} · {item.fault_type ?? '—'} · {item.priority ?? '—'}
                      </p>
                    </div>
                    {assignFor === item.id ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <Select
                          className="!w-auto py-1.5 text-xs"
                          value={teamId}
                          onChange={(e) => setTeamId(e.target.value)}
                        >
                          {teams.map((t) => (
                            <option key={t.team_id} value={t.team_id}>
                              {t.team_name} (yük {t.active_load})
                            </option>
                          ))}
                        </Select>
                        <Button size="sm" variant="success" disabled={busy} onClick={() => void onAssign()}>
                          Onayla
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setAssignFor(null)}>
                          İptal
                        </Button>
                      </div>
                    ) : (
                      <Button size="sm" variant="primary" onClick={() => setAssignFor(item.id)}>
                        Manuel ata
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </AppShell>
  )
}
