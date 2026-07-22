import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { PredictResponse, TelemetryInput } from '../api/types'
import {
  FaultType as FT,
  PowerStatus,
  PredictionMethod,
  Priority as P,
  Suggestion,
} from '../api/types'
import { CRITICAL_TELEMETRY, listIncidents, submitTelemetry } from '../api/incidentApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { Button, Card, Field, Input, Select } from '../components/ui'
import { EmptyState } from '../components/UiStates'

interface PredictionRow {
  id: string
  at: string
  station_code: string
  prediction: PredictResponse
  caseStatus: 'none' | 'pending_approval' | 'opened' | 'auto_opened'
  incident_number?: string
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

export function NocDashboardPage() {
  const [form, setForm] = useState<TelemetryInput>(emptyForm)
  const [rows, setRows] = useState<PredictionRow[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)

  function setField<K extends keyof TelemetryInput>(key: K, value: TelemetryInput[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  useEffect(() => {
    // Tahmin listesi oncesi bu oturuma ozeldi (sayfa degisince kayboluyordu) - artik
    // mount'ta backend'deki gercek vaka gecmisini cekip gosteriyoruz.
    let cancelled = false
    async function loadHistory() {
      try {
        const incidents = await listIncidents()
        if (cancelled) return
        const historyRows: PredictionRow[] = incidents.map((i) => ({
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
              : 'Geçmiş kayıt (henüz atanmadı).',
          },
          caseStatus: i.assigned_team_id ? 'auto_opened' : 'pending_approval',
          incident_number: i.incident_number,
        }))
        setRows(historyRows)
      } catch {
        /* gecmis yuklenemedi - liste bos kalir, kullanici yeni telemetri gonderebilir */
      }
    }
    void loadHistory()
    return () => {
      cancelled = true
    }
  }, [])

  async function runTelemetry(input: TelemetryInput) {
    setBusy(true)
    setError(null)
    setFlash(null)
    try {
      const result = await submitTelemetry(input)
      const prediction = result.prediction
      if (!prediction) throw new Error('Tahmin alınamadı')

      let caseStatus: PredictionRow['caseStatus'] = 'none'
      if (prediction.suggestion === Suggestion.ACIL) caseStatus = 'auto_opened'
      else if (prediction.suggestion === Suggestion.VAKA_AC) caseStatus = 'pending_approval'
      else caseStatus = 'none'

      if (result.incident && prediction.suggestion === Suggestion.ACIL) {
        caseStatus = 'auto_opened'
      }

      const row: PredictionRow = {
        id: result.telemetry_id,
        at: new Date().toISOString(),
        station_code: input.station_code,
        prediction,
        caseStatus,
        incident_number: result.incident?.incident_number,
      }
      setRows((prev) => [row, ...prev])
      setFlash(
        prediction.suggestion === Suggestion.ACIL
          ? 'Kritik tahmin — vaka otomatik açıldı / atandı (simülasyon).'
          : prediction.suggestion === Suggestion.VAKA_AC
            ? 'Operatör onayı bekleniyor (VAKA_AC).'
            : 'İzleme önerisi (IZLE) — vaka açılmadı.',
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

  function approveCase(id: string) {
    setRows((prev) =>
      prev.map((r) =>
        r.id === id
          ? {
              ...r,
              caseStatus: 'opened',
              incident_number: r.incident_number ?? `INC-2026-${String(Date.now()).slice(-6)}`,
            }
          : r,
      ),
    )
    setFlash('Vaka onaylandı / açıldı (NOC). Backend atama CP4 ile tamamlanır.')
  }

  return (
    <AppShell title="NetOpsCell — NOC" subtitle="Telemetri simülatörü">
      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-semibold">Telemetri gönder</h2>
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
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold">Tahmin listesi</h2>
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
                    {r.caseStatus === 'pending_approval' && (
                      <>
                        <Button variant="success" size="sm" onClick={() => approveCase(r.id)}>
                          Vaka aç / onayla
                        </Button>
                        <span className="text-xs text-amber-600 dark:text-amber-400">Onay bekliyor</span>
                      </>
                    )}
                    {r.caseStatus === 'auto_opened' && (
                      <span className="text-xs font-medium text-rose-600 dark:text-rose-400">
                        ACIL — otomatik vaka {r.incident_number ?? ''}
                      </span>
                    )}
                    {r.caseStatus === 'opened' && (
                      <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                        Açıldı {r.incident_number ?? ''}
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
