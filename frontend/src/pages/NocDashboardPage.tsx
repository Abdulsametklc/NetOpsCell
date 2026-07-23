import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { IncidentListItem, PredictResponse, TelemetryInput } from '../api/types'
import {
  FaultType as FT,
  PowerStatus,
  PredictionMethod,
  Priority as P,
  Suggestion,
} from '../api/types'
import { CRITICAL_TELEMETRY, listIncidents, submitEvaluation, submitTelemetry } from '../api/incidentApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { Button, Card, Field, Input, Select } from '../components/ui'
import { EmptyState } from '../components/UiStates'
import { useToastStore } from '../store/toastStore'

interface PredictionRow {
  id: string
  at: string
  station_code: string
  prediction: PredictResponse
  caseStatus: 'none' | 'assigned' | 'queued'
  incident_number?: string
  assigned_team_name?: string | null
}

const emptyForm: TelemetryInput = {
  station_code: 'IST-AVR-042',
  lat: 41.0082,
  lng: 28.9784,
  signal_strength: -85,
  packet_loss: 2,
  temperature: 42,
  power_status: PowerStatus.NORMAL,
  recent_fault_count: 0,
}

function suggestionClass(s: Suggestion): string {
  if (s === Suggestion.ACIL) return 'text-rose-600 dark:text-rose-400'
  if (s === Suggestion.VAKA_AC) return 'text-amber-600 dark:text-amber-400'
  return 'text-slate-500 dark:text-slate-400'
}

function toPredictionRow(i: IncidentListItem): PredictionRow {
  return {
    id: i.id,
    at: i.created_at ?? new Date().toISOString(),
    station_code: i.station_code,
    prediction: {
      probability: i.probability ?? 0,
      fault_type: (i.fault_type as PredictResponse['fault_type']) ?? FT.BELIRSIZ,
      priority: (i.priority as PredictResponse['priority']) ?? P.ORTA,
      suggestion: (i.ai_suggestion as Suggestion) ?? Suggestion.VAKA_AC,
      method: PredictionMethod.RULE_FALLBACK,
      confidence_explanation: i.assigned_team_name
        ? `Atanan ekip: ${i.assigned_team_name}`
        : 'Bekleyen atama kuyruğunda (uygun ekip bulunamadı).',
    },
    caseStatus: i.assigned_team_id ? 'assigned' : 'queued',
    incident_number: i.incident_number,
    assigned_team_name: i.assigned_team_name,
  }
}

export function NocDashboardPage() {
  const pushToast = useToastStore((s) => s.push)
  const [form, setForm] = useState<TelemetryInput>(emptyForm)
  const [rows, setRows] = useState<PredictionRow[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)

  const [pendingEval, setPendingEval] = useState<IncidentListItem[]>([])
  const [evalDraft, setEvalDraft] = useState<Record<string, { stars: number; isPermanent: boolean }>>({})
  const [evalSubmitting, setEvalSubmitting] = useState<string | null>(null)

  function setField<K extends keyof TelemetryInput>(key: K, value: TelemetryInput[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function loadHistory() {
    try {
      const incidents = await listIncidents()
      setRows(incidents.map(toPredictionRow))
      const closed = incidents.filter((i) => i.current_status === 'KAPANDI' && !i.has_evaluation)
      setPendingEval(closed)
      setEvalDraft((prev) => {
        const next = { ...prev }
        for (const i of closed) if (!next[i.id]) next[i.id] = { stars: 5, isPermanent: true }
        return next
      })
    } catch {
      /* gecmis yuklenemedi - liste bos kalir, kullanici yeni telemetri gonderebilir */
    }
  }

  useEffect(() => {
    // mount'ta backend'deki gercek vaka gecmisini + degerlendirme bekleyen kapanan vakalari cekiyoruz.
    void loadHistory()
  }, [])

  async function runTelemetry(input: TelemetryInput) {
    setBusy(true)
    setError(null)
    setFlash(null)
    try {
      const result = await submitTelemetry(input)
      const prediction = result.prediction
      if (!prediction) throw new Error('Tahmin alınamadı')

      const row: PredictionRow = {
        id: result.telemetry_id,
        at: new Date().toISOString(),
        station_code: input.station_code,
        prediction,
        caseStatus: result.incident ? (result.incident.assigned_team_name ? 'assigned' : 'queued') : 'none',
        incident_number: result.incident?.incident_number,
        assigned_team_name: result.incident?.assigned_team_name,
      }
      setRows((prev) => [row, ...prev])
      setFlash(
        !result.incident
          ? 'İzleme önerisi (IZLE) — vaka açılmadı.'
          : result.incident.assigned_team_name
            ? `Vaka ${result.incident.incident_number} açıldı ve ${result.incident.assigned_team_name} ekibine otomatik atandı.`
            : `Vaka ${result.incident.incident_number} açıldı, uygun ekip bulunamadı — bekleyen atama kuyruğunda (Süpervizör Dashboard).`,
      )
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Telemetri hatası')
    } finally {
      setBusy(false)
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    await runTelemetry(form)
  }

  async function onCritical() {
    setForm(CRITICAL_TELEMETRY)
    await runTelemetry(CRITICAL_TELEMETRY)
  }

  async function onEvaluate(id: string) {
    const draft = evalDraft[id] ?? { stars: 5, isPermanent: true }
    setEvalSubmitting(id)
    try {
      await submitEvaluation(id, draft.stars, draft.isPermanent)
      setPendingEval((prev) => prev.filter((i) => i.id !== id))
      pushToast('success', 'Değerlendirme kaydedildi', 'Saha ekibine puanı yansıtıldı.')
    } catch (err) {
      pushToast('warning', 'Değerlendirme gönderilemedi', err instanceof Error ? err.message : 'Hata')
    } finally {
      setEvalSubmitting(null)
    }
  }

  return (
    <AppShell title="NetOpsCell — NOC" subtitle="Telemetri simülatörü">
      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-xl font-bold">Telemetri gönder</h2>
          <Card as="form" onSubmit={onSubmit} className="space-y-3 p-4">
            {(
              [
                ['station_code', 'İstasyon', 'text'],
                ['lat', 'Lat', 'number'],
                ['lng', 'Lng', 'number'],
                ['signal_strength', 'Sinyal (dBm)', 'number'],
                ['packet_loss', 'Paket kaybı %', 'number'],
                ['temperature', 'Sıcaklık °C', 'number'],
                ['recent_fault_count', 'Son 24s arıza', 'number'],
              ] as const
            ).map(([key, label, type]) => (
              <Field key={key} label={label}>
                <Input
                  type={type}
                  value={form[key] as string | number}
                  onChange={(e) => setField(key, type === 'number' ? Number(e.target.value) : e.target.value)}
                  required
                />
              </Field>
            ))}
            <Field label="Güç durumu">
              <Select value={form.power_status} onChange={(e) => setField('power_status', e.target.value as PowerStatus)}>
                <option value={PowerStatus.NORMAL}>NORMAL</option>
                <option value={PowerStatus.KESINTIDE}>KESINTIDE</option>
              </Select>
            </Field>

            <div className="flex flex-wrap gap-2 pt-2">
              <Button type="submit" variant="primary" disabled={busy}>
                {busy ? 'Gönderiliyor…' : 'Telemetri gönder'}
              </Button>
              <Button type="button" variant="danger" disabled={busy} onClick={onCritical}>
                Kritik telemetri (demo)
              </Button>
            </div>
          </Card>
          {error && (
            <p className="mt-3 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300" role="alert">
              {error}
            </p>
          )}
          {flash && (
            <p className="mt-3 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300" role="status">
              {flash}
            </p>
          )}

          <h2 className="mb-3 mt-6 text-xl font-bold">Çözümü değerlendir</h2>
          <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
            Kapanan vakalar için tek seferlik değerlendirme — kalıcı çözüm mü, geçici mi (bkz. case §4.6).
          </p>
          {pendingEval.length === 0 ? (
            <EmptyState message="Değerlendirilecek kapanmış vaka yok." />
          ) : (
            <ul className="space-y-3">
              {pendingEval.map((i) => {
                const draft = evalDraft[i.id] ?? { stars: 5, isPermanent: true }
                return (
                  <Card key={i.id} className="p-4 text-sm">
                    <div className="mb-2 flex justify-between gap-2">
                      <span className="font-mono text-tc-navy-700 dark:text-tc-yellow-400">{i.incident_number}</span>
                      <span className="text-xs text-slate-500 dark:text-slate-400">{i.assigned_team_name}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((n) => (
                          <button
                            key={n}
                            type="button"
                            aria-label={`${n} yıldız`}
                            onClick={() => setEvalDraft((prev) => ({ ...prev, [i.id]: { ...draft, stars: n } }))}
                            className={`text-lg ${n <= draft.stars ? 'text-tc-yellow-500' : 'text-slate-300 dark:text-tc-navy-700'}`}
                          >
                            ★
                          </button>
                        ))}
                      </div>
                      <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                        <input
                          type="checkbox"
                          checked={draft.isPermanent}
                          onChange={(e) =>
                            setEvalDraft((prev) => ({ ...prev, [i.id]: { ...draft, isPermanent: e.target.checked } }))
                          }
                        />
                        Kalıcı çözüm
                      </label>
                      <Button
                        size="sm"
                        variant="success"
                        disabled={evalSubmitting === i.id}
                        onClick={() => void onEvaluate(i.id)}
                      >
                        {evalSubmitting === i.id ? 'Gönderiliyor…' : 'Değerlendir'}
                      </Button>
                    </div>
                  </Card>
                )
              })}
            </ul>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-xl font-bold">Tahmin listesi</h2>
          {rows.length === 0 ? (
            <EmptyState message="Henüz tahmin yok — telemetri gönderin." />
          ) : (
            <ul className="space-y-3">
              {rows.map((r) => (
                <Card key={r.id} className="p-4 text-sm">
                  <div className="mb-2 flex justify-between gap-2">
                    <span className="font-mono text-tc-navy-700 dark:text-tc-yellow-400">{r.station_code}</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(r.at).toLocaleTimeString('tr-TR')}
                    </span>
                  </div>
                  <p>
                    <span className="text-slate-500 dark:text-slate-400">Olasılık:</span>{' '}
                    {(r.prediction.probability * 100).toFixed(0)}% ·{' '}
                    <span className="font-medium">{r.prediction.fault_type}</span> ·{' '}
                    <span className="font-medium">{r.prediction.priority}</span> ·{' '}
                    <span className={`font-medium ${suggestionClass(r.prediction.suggestion)}`}>
                      {r.prediction.suggestion}
                    </span>
                  </p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{r.prediction.confidence_explanation}</p>
                  <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">method: {r.prediction.method}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {r.caseStatus === 'assigned' && (
                      <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                        Vaka {r.incident_number} — {r.assigned_team_name} ekibine atandı
                      </span>
                    )}
                    {r.caseStatus === 'queued' && (
                      <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
                        Vaka {r.incident_number} açıldı — bekleyen atama kuyruğunda
                      </span>
                    )}
                    {r.caseStatus === 'none' && (
                      <span className="text-xs text-slate-400 dark:text-slate-500">IZLE — aksiyon yok</span>
                    )}
                  </div>
                </Card>
              ))}
            </ul>
          )}
        </section>
      </div>
    </AppShell>
  )
}
