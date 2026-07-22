import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import type { PredictResponse, TelemetryInput } from '../api/types'
import { PowerStatus, Suggestion } from '../api/types'
import {
  CRITICAL_TELEMETRY,
  incidentModeLabel,
  submitTelemetry,
} from '../api/incidentApi'
import { logout } from '../api/authApi'
import { ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'

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

export function NocDashboardPage() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [form, setForm] = useState<TelemetryInput>(emptyForm)
  const [rows, setRows] = useState<PredictionRow[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  function setField<K extends keyof TelemetryInput>(key: K, value: TelemetryInput[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

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
              incident_number:
                r.incident_number ?? `INC-2026-${String(Date.now()).slice(-6)}`,
            }
          : r,
      ),
    )
    setFlash('Vaka onaylandı / açıldı (NOC). Backend atama CP4 ile tamamlanır.')
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between gap-4">
        <div>
          <p className="text-lg font-semibold tracking-tight">NetOpsCell — NOC</p>
          <p className="text-xs text-slate-500">Telemetri simülatörü · {incidentModeLabel()}</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-400">
            {user?.first_name ?? 'NOC'} · {user?.role}
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

      <div className="max-w-6xl mx-auto px-6 py-6 grid gap-8 lg:grid-cols-2">
        <section>
          <h2 className="text-lg font-medium mb-3">Telemetri gönder</h2>
          <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
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
              <label key={key} className="block text-sm">
                <span className="text-slate-400">{label}</span>
                <input
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  type={type}
                  value={form[key] as string | number}
                  onChange={(e) =>
                    setField(
                      key,
                      type === 'number' ? Number(e.target.value) : e.target.value,
                    )
                  }
                  required
                />
              </label>
            ))}
            <label className="block text-sm">
              <span className="text-slate-400">Güç durumu</span>
              <select
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                value={form.power_status}
                onChange={(e) => setField('power_status', e.target.value as PowerStatus)}
              >
                <option value={PowerStatus.NORMAL}>NORMAL</option>
                <option value={PowerStatus.KESINTIDE}>KESINTIDE</option>
              </select>
            </label>

            <div className="flex flex-wrap gap-2 pt-2">
              <button
                type="submit"
                disabled={busy}
                className="rounded bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-60"
              >
                {busy ? 'Gönderiliyor…' : 'Telemetri gönder'}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={onCritical}
                className="rounded bg-rose-700 px-4 py-2 text-sm font-medium hover:bg-rose-600 disabled:opacity-60"
              >
                Kritik telemetri (demo)
              </button>
            </div>
          </form>
          {error && (
            <p className="mt-3 text-sm text-rose-400" role="alert">
              {error}
            </p>
          )}
          {flash && (
            <p className="mt-3 text-sm text-emerald-400" role="status">
              {flash}
            </p>
          )}
        </section>

        <section>
          <h2 className="text-lg font-medium mb-3">Tahmin listesi</h2>
          {rows.length === 0 ? (
            <p className="text-sm text-slate-500">Henüz tahmin yok — telemetri gönderin.</p>
          ) : (
            <ul className="space-y-3">
              {rows.map((r) => (
                <li
                  key={r.id}
                  className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-sm"
                >
                  <div className="flex justify-between gap-2 mb-2">
                    <span className="font-mono text-sky-300">{r.station_code}</span>
                    <span className="text-xs text-slate-500">
                      {new Date(r.at).toLocaleTimeString('tr-TR')}
                    </span>
                  </div>
                  <p>
                    <span className="text-slate-400">Olasılık:</span>{' '}
                    {(r.prediction.probability * 100).toFixed(0)}% ·{' '}
                    <span className="text-amber-300">{r.prediction.fault_type}</span> ·{' '}
                    <span className="text-orange-300">{r.prediction.priority}</span> ·{' '}
                    <span className="text-rose-300">{r.prediction.suggestion}</span>
                  </p>
                  <p className="mt-1 text-slate-400 text-xs">{r.prediction.confidence_explanation}</p>
                  <p className="mt-1 text-xs text-slate-500">method: {r.prediction.method}</p>
                  <div className="mt-3 flex flex-wrap gap-2 items-center">
                    {r.caseStatus === 'pending_approval' && (
                      <>
                        <button
                          type="button"
                          className="rounded bg-emerald-700 px-3 py-1.5 text-xs hover:bg-emerald-600"
                          onClick={() => approveCase(r.id)}
                        >
                          Vaka aç / onayla
                        </button>
                        <span className="text-xs text-amber-400">Onay bekliyor</span>
                      </>
                    )}
                    {r.caseStatus === 'auto_opened' && (
                      <span className="text-xs text-rose-400">
                        ACIL — otomatik vaka {r.incident_number ?? ''}
                      </span>
                    )}
                    {r.caseStatus === 'opened' && (
                      <span className="text-xs text-emerald-400">
                        Açıldı {r.incident_number ?? ''}
                      </span>
                    )}
                    {r.caseStatus === 'none' && (
                      <span className="text-xs text-slate-500">IZLE — aksiyon yok</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  )
}
