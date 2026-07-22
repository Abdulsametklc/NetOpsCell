import { useEffect, useState } from 'react'
import type { IncidentListItem } from '../api/types'
import { IncidentStatus } from '../api/types'
import { incidentModeLabel, listIncidents, patchIncidentStatus } from '../api/incidentApi'
import { ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
import { MessageThread } from '../components/MessageThread'
import { SlaBadge } from '../components/SlaBadge'
import { Button, Card, Textarea } from '../components/ui'
import { allowedNextStatuses, requiresResolutionNote, statusActionLabel } from '../lib/stateMachine'

function priorityClass(priority: string | null | undefined): string {
  switch (priority) {
    case 'KRITIK':
      return 'text-rose-600 dark:text-rose-400'
    case 'YUKSEK':
      return 'text-orange-600 dark:text-orange-400'
    case 'ORTA':
      return 'text-amber-600 dark:text-amber-400'
    default:
      return 'text-slate-500 dark:text-slate-400'
  }
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
  const [threadOpen, setThreadOpen] = useState<string | null>(null)

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
      setIncidents((prev) =>
        prev.map((i) =>
          i.id === id
            ? {
                ...i,
                ...updated,
                sla_status: to === IncidentStatus.COZULDU ? 'MET' : (updated.sla_status ?? i.sla_status),
              }
            : i,
        ),
      )
      setNoteFor(null)
      setPendingTo(null)
      setNote('')
      if (to === IncidentStatus.COZULDU) {
        pushToast('success', 'Vaka çözüldü', 'Çözüm notu kaydedildi.')
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
        <h2 className="text-xl font-semibold">Atanan arızalar</h2>
        <Button variant="secondary" size="sm" onClick={() => void load()}>
          Yenile
        </Button>
      </div>

      {loading && <LoadingState />}
      {error && (
        <div className="mb-3">
          <ErrorState message={error} />
        </div>
      )}
      {!loading && !error && incidents.length === 0 && <EmptyState message="Atanmış vaka yok." />}
      {!loading && incidents.length > 0 && (
        <div className="space-y-4">
          {incidents.map((item) => {
            const next = allowedNextStatuses(String(item.current_status), role)
            const open = threadOpen === item.id
            return (
              <Card key={item.id} className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-mono text-tc-navy-700 dark:text-tc-yellow-400">{item.incident_number}</h3>
                  <div className="flex flex-wrap items-center gap-2">
                    <SlaBadge slaDueAt={item.sla_due_at} slaStatus={item.sla_status} />
                    <span className={`text-sm font-semibold ${priorityClass(item.priority)}`}>
                      {item.priority ?? '—'}
                    </span>
                  </div>
                </div>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  {item.station_code} · {item.fault_type ?? '—'} ·{' '}
                  <span className="text-slate-500 dark:text-slate-400">{item.current_status}</span>
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {next.length === 0 && (
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      Bu durumda teknisyen aksiyonu yok
                      {item.current_status === IncidentStatus.PARCA_BEKLENIYOR
                        ? ' (parça tedariki bekleniyor)'
                        : ''}
                    </span>
                  )}
                  {next.map((to) => (
                    <Button
                      key={to}
                      size="sm"
                      variant="primary"
                      disabled={busyId === item.id}
                      onClick={() => requestTransition(item, to)}
                    >
                      {statusActionLabel(to)}
                    </Button>
                  ))}
                  <Button size="sm" variant="secondary" onClick={() => setThreadOpen(open ? null : item.id)}>
                    {open ? 'Mesajları gizle' : 'Mesajlaşma'}
                  </Button>
                </div>
                {noteFor === item.id && (
                  <div className="mt-3 space-y-2 border-t border-slate-200 pt-3 dark:border-tc-navy-800">
                    <label className="block text-sm">
                      <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
                        Çözüm notu (zorunlu)
                      </span>
                      <Textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Yapılan müdahale…"
                      />
                    </label>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="success"
                        disabled={!note.trim() || busyId === item.id}
                        onClick={() => pendingTo && void applyTransition(item.id, pendingTo, note.trim())}
                      >
                        Kaydet ve çöz
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setNoteFor(null)
                          setPendingTo(null)
                        }}
                      >
                        İptal
                      </Button>
                    </div>
                  </div>
                )}
                {open && <MessageThread incidentId={item.id} incidentNumber={item.incident_number} />}
              </Card>
            )
          })}
        </div>
      )}
    </AppShell>
  )
}
