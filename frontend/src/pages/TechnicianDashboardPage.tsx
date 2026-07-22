import { useNavigate } from 'react-router-dom'
import { mockAssignedIncidents } from '../api/mocks/incidents'
import type { IncidentListItem } from '../api/types'
import { logout } from '../api/authApi'
import { useAuthStore } from '../store/authStore'

function priorityClass(priority: string | null | undefined): string {
  switch (priority) {
    case 'KRITIK':
      return 'text-rose-400'
    case 'YUKSEK':
      return 'text-orange-400'
    case 'ORTA':
      return 'text-amber-300'
    default:
      return 'text-slate-400'
  }
}

function slaLabel(iso: string | null | undefined): { text: string; className: string } {
  if (!iso) return { text: '—', className: 'text-slate-500' }
  const ms = new Date(iso).getTime() - Date.now()
  if (ms < 0) return { text: 'SLA aşıldı', className: 'text-rose-400' }
  const min = Math.round(ms / 60000)
  if (min < 60) return { text: `${min} dk`, className: 'text-amber-300' }
  return { text: `${Math.round(min / 60)} sa`, className: 'text-emerald-400' }
}

function IncidentRow({ item }: { item: IncidentListItem }) {
  const sla = slaLabel(item.sla_due_at)
  return (
    <tr className="border-b border-slate-800/80">
      <td className="py-3 pr-4 font-mono text-sm text-sky-300">{item.incident_number}</td>
      <td className="py-3 pr-4 text-sm">{item.station_code}</td>
      <td className="py-3 pr-4 text-sm">{item.fault_type ?? '—'}</td>
      <td className={`py-3 pr-4 text-sm font-medium ${priorityClass(item.priority)}`}>
        {item.priority ?? '—'}
      </td>
      <td className="py-3 pr-4 text-sm text-slate-300">{item.current_status}</td>
      <td className={`py-3 text-sm ${sla.className}`}>{sla.text}</td>
    </tr>
  )
}

export function TechnicianDashboardPage() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const incidents = mockAssignedIncidents

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between gap-4">
        <div>
          <p className="text-lg font-semibold tracking-tight">NetOpsCell</p>
          <p className="text-xs text-slate-500">Saha Teknisyeni — atanan vakalar (mock)</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-400">
            {user?.first_name ?? 'Kullanıcı'} · {user?.role}
          </span>
          <button
            type="button"
            onClick={onLogout}
            className="rounded border border-slate-700 px-3 py-1.5 hover:bg-slate-900"
          >
            Çıkış
          </button>
        </div>
      </header>

      <section className="px-6 py-6 max-w-5xl mx-auto">
        <h2 className="text-xl font-medium mb-4">Atanan arızalar</h2>
        {incidents.length === 0 ? (
          <p className="text-slate-500 text-sm">Atanmış vaka yok.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left">
              <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-3 px-4 font-medium">No</th>
                  <th className="py-3 px-4 font-medium">İstasyon</th>
                  <th className="py-3 px-4 font-medium">Tür</th>
                  <th className="py-3 px-4 font-medium">Öncelik</th>
                  <th className="py-3 px-4 font-medium">Durum</th>
                  <th className="py-3 px-4 font-medium">SLA</th>
                </tr>
              </thead>
              <tbody className="px-4">
                {incidents.map((item) => (
                  <IncidentRow key={item.id} item={item} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-4 text-xs text-slate-600">
          CP3: liste <code className="text-slate-500">GET /api/v1/incidents?assigned_to_me=true</code>{' '}
          ile gerçek API’ye bağlanacak.
        </p>
      </section>
    </main>
  )
}
