import { useEffect, useState } from 'react'
import type { IncidentListItem } from '../api/types'
import { IncidentStatus } from '../api/types'
import { incidentModeLabel, listIncidents, patchIncidentStatus } from '../api/incidentApi'
import { ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
import {
  allowedNextStatuses,
  requiresResolutionNote,
  statusActionLabel,
} from '../lib/stateMachine'

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

export function TechnicianDashboardPage() {
  const user = useAuthStore((s) => s.user)
  const role = user?.role
  const pushToast = useToastStore((s) => s.push)
  const [incidents, setIncidents] = useState<IncidentListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [noteFor, setNoteFor] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [pendingTo, setPendingTo] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await listIncidents({ assigned_to_me: true })
      setIncidents(data)
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Liste alınamadı')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  function requestTransition(item: IncidentListItem, to: string) {
    if (requiresResolutionNote(to)) {
      setNoteFor(item.id)
      setPendingTo(to)
      setNote('')
      return
    }
    void applyTransition(item.id, to)
  }

  async function applyTransition(id: string, to: string, resolution_note?: string) {
    setBusyId(id)
    setError(null)
    try {
      const updated = await patchIncidentStatus(id, to, resolution_note)
      setIncidents((prev) => prev.map((i) => (i.id === id ? { ...i, ...updated } : i)))
      setNoteFor(null)
      setPendingTo(null)
      setNote('')
      if (to === IncidentStatus.COZULDU) {
        pushToast(
          'success',
          'Vaka çözüldü',
          'Puan gamification ile işlenecek; liderlik tablosunu kontrol edin.',
        )
        pushToast('badge', 'Rozet kontrolü', 'Uygunsa rozet toast’ı CP5 WS ile gelecek (şimdilik yerel).')
      } else {
        pushToast('info', 'Durum güncellendi', statusActionLabel(to))
      }
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Güncelleme hatası')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <AppShell title="NetOpsCell — Teknisyen" subtitle={incidentModeLabel()}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-xl font-medium">Atanan arızalar</h2>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900"
        >
          Yenile
        </button>
      </div>

      {loading && <LoadingState />}
      {error && (
        <div className="mb-3">
          <ErrorState message={error} />
        </div>
      )}
      {!loading && !error && incidents.length === 0 && (
        <EmptyState message="Atanmış vaka yok." />
      )}
      {!loading && incidents.length > 0 && (
        <div className="space-y-4">
          {incidents.map((item) => {
            const sla = slaLabel(item.sla_due_at)
            const next = allowedNextStatuses(String(item.current_status), role)
            return (
              <article
                key={item.id}
                className="rounded-lg border border-slate-800 bg-slate-900/40 p-4"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-mono text-sky-300">{item.incident_number}</h3>
                  <span className={`text-sm font-medium ${priorityClass(item.priority)}`}>
                    {item.priority ?? '—'}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-300">
                  {item.station_code} · {item.fault_type ?? '—'} ·{' '}
                  <span className="text-slate-400">{item.current_status}</span>
                  {' · SLA '}
                  <span className={sla.className}>{sla.text}</span>
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {next.length === 0 && (
                    <span className="text-xs text-slate-500">
                      Bu durumda teknisyen aksiyonu yok
                      {item.current_status === IncidentStatus.PARCA_BEKLENIYOR
                        ? ' (parça tedariki bekleniyor)'
                        : ''}
                    </span>
                  )}
                  {next.map((to) => (
                    <button
                      key={to}
                      type="button"
                      disabled={busyId === item.id}
                      onClick={() => requestTransition(item, to)}
                      className="rounded bg-sky-700 px-3 py-1.5 text-xs font-medium hover:bg-sky-600 disabled:opacity-60"
                    >
                      {statusActionLabel(to)}
                    </button>
                  ))}
                </div>
                {noteFor === item.id && (
                  <div className="mt-3 space-y-2 border-t border-slate-800 pt-3">
                    <label className="block text-sm">
                      <span className="text-slate-400">Çözüm notu (zorunlu)</span>
                      <textarea
                        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Yapılan müdahale…"
                      />
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={!note.trim() || busyId === item.id}
                        className="rounded bg-emerald-700 px-3 py-1.5 text-xs disabled:opacity-60"
                        onClick={() =>
                          pendingTo && void applyTransition(item.id, pendingTo, note.trim())
                        }
                      >
                        Kaydet ve çöz
                      </button>
                      <button
                        type="button"
                        className="rounded border border-slate-700 px-3 py-1.5 text-xs"
                        onClick={() => {
                          setNoteFor(null)
                          setPendingTo(null)
                        }}
                      >
                        İptal
                      </button>
                    </div>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </AppShell>
  )
}
