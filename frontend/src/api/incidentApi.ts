import type {
  FaultType,
  IncidentListItem,
  IncidentStatus,
  PowerStatus,
  PredictResponse,
  Priority,
  ResponseEnvelope,
  Suggestion,
  TelemetryInput,
} from './types'
import {
  FaultType as FT,
  PredictionMethod,
  Priority as P,
  Suggestion as S,
} from './types'
import { apiFetch, getApiBaseUrl } from './client'
import { mockAssignedIncidents } from './mocks/incidents'
import { mockPredictSuccess } from './mocks/predict'

function useIncidentMock(): boolean {
  return import.meta.env.VITE_USE_INCIDENT_MOCK === 'true'
}

export interface TelemetrySubmitResult {
  telemetry_id: string
  prediction?: PredictResponse | null
  incident?: IncidentListItem | null
}

/** Deterministik istemci fallback — backend AI yokken demo için (girdiye göre değişir) */
export function localPredict(input: TelemetryInput): PredictResponse {
  let score = 0
  if (input.temperature >= 75) score += 0.45
  else if (input.temperature >= 60) score += 0.25
  if (input.packet_loss >= 20) score += 0.35
  else if (input.packet_loss >= 8) score += 0.15
  if (input.signal_strength <= -105) score += 0.2
  else if (input.signal_strength <= -95) score += 0.1
  if (input.power_status === 'KESINTIDE') score += 0.4
  score += Math.min(0.15, (input.recent_fault_count ?? 0) * 0.05)
  const probability = Math.min(0.99, Math.round(score * 100) / 100)

  let fault_type: FaultType = FT.BELIRSIZ
  if (input.power_status === 'KESINTIDE') fault_type = FT.GUC_KESINTISI
  else if (input.temperature >= 70) fault_type = FT.ISINMA
  else if (input.packet_loss >= 15 || input.signal_strength <= -105) fault_type = FT.BAGLANTI
  else if (probability >= 0.4) fault_type = FT.DONANIM

  let suggestion: Suggestion = S.IZLE
  let priority: Priority = P.DUSUK
  if (probability > 0.85) {
    suggestion = S.ACIL
    priority = P.KRITIK
  } else if (probability >= 0.4) {
    suggestion = S.VAKA_AC
    priority = probability >= 0.7 ? P.YUKSEK : P.ORTA
  }

  return {
    probability,
    fault_type,
    priority,
    suggestion,
    method: PredictionMethod.RULE_FALLBACK,
    confidence_explanation: `Sıcaklık ${input.temperature}°C, kayıp %${input.packet_loss}, sinyal ${input.signal_strength} dBm → skor ${probability}.`,
  }
}

export const CRITICAL_TELEMETRY: TelemetryInput = {
  station_code: 'IST-AVR-099',
  lat: 41.015,
  lng: 28.979,
  signal_strength: -112,
  packet_loss: 42,
  temperature: 88,
  power_status: 'KESINTIDE' as PowerStatus,
  recent_fault_count: 3,
}

export async function submitTelemetry(
  input: TelemetryInput,
): Promise<TelemetrySubmitResult> {
  if (useIncidentMock()) {
    const prediction = localPredict(input)
    const telemetry_id = `mock-tel-${Date.now()}`
    let incident: IncidentListItem | null = null
    if (prediction.suggestion === 'ACIL' || prediction.suggestion === 'VAKA_AC') {
      incident = {
        id: `mock-inc-${Date.now()}`,
        incident_number: `INC-2026-${String(Date.now()).slice(-6)}`,
        station_code: input.station_code,
        current_status: prediction.suggestion === 'ACIL' ? 'ATANDI' : 'YENI',
        fault_type: prediction.fault_type,
        priority: prediction.priority,
        assigned_team_name: prediction.suggestion === 'ACIL' ? 'IST-AVRUPA-A' : null,
      }
    }
    return { telemetry_id, prediction, incident }
  }

  const envelope = await apiFetch<{
    telemetry_id: string
    prediction?: PredictResponse
    incident?: IncidentListItem
  }>('/api/v1/telemetry', {
    method: 'POST',
    body: JSON.stringify(input),
  })

  const data = envelope.data
  if (!data) throw new Error('Telemetri cevabı boş')

  // Backend henüz prediction dönmüyorsa istemci kuralı ile zenginleştir (demo)
  const prediction = data.prediction ?? localPredict(input)
  return {
    telemetry_id: data.telemetry_id,
    prediction,
    incident: data.incident ?? null,
  }
}

export async function listIncidents(params?: {
  assigned_to_me?: boolean
}): Promise<IncidentListItem[]> {
  if (useIncidentMock()) {
    return mockAssignedIncidents
  }

  const q = new URLSearchParams()
  if (params?.assigned_to_me) q.set('assigned_to_me', 'true')
  const path = `/api/v1/incidents${q.toString() ? `?${q}` : ''}`
  const envelope = await apiFetch<IncidentListItem[]>(path)
  return envelope.data ?? []
}

export async function patchIncidentStatus(
  id: string,
  to_status: IncidentStatus | string,
  resolution_note?: string,
): Promise<IncidentListItem> {
  if (useIncidentMock()) {
    const item = mockAssignedIncidents.find((i) => i.id === id)
    if (!item) throw new Error('Vaka bulunamadı (mock)')
    item.current_status = to_status
    return { ...item }
  }

  const body: Record<string, string> = { status: to_status }
  if (resolution_note) body.resolution_note = resolution_note

  const envelope = await apiFetch<IncidentListItem>(`/api/v1/incidents/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!envelope.data) throw new Error('Durum güncelleme cevabı boş')
  return envelope.data
}

export function incidentModeLabel(): string {
  return useIncidentMock()
    ? `mock incident (${getApiBaseUrl()})`
    : `live API (${getApiBaseUrl()})`
}

export type { ResponseEnvelope }
export { mockPredictSuccess }
