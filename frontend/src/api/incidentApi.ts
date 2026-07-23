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
  ai_available?: boolean
}

/** Deterministik istemci fallback — yalnızca mock veya prediction eksikse */
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

function predictionFromIncident(
  incident: IncidentListItem,
  input: TelemetryInput,
): PredictResponse {
  const suggestion = (incident.ai_suggestion as Suggestion | null) ?? S.VAKA_AC
  return {
    probability: incident.probability ?? 0,
    fault_type: (incident.fault_type as FaultType) ?? FT.BELIRSIZ,
    priority: (incident.priority as Priority) ?? P.ORTA,
    suggestion,
    method: PredictionMethod.RULE_FALLBACK,
    confidence_explanation:
      suggestion === S.IZLE
        ? 'İzleme — vaka açılmadı.'
        : `Incident Service / AI: ${incident.fault_type ?? 'BELIRSIZ'} · ${incident.priority ?? 'ORTA'} (istasyon ${input.station_code}).`,
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

type TelemetryApiData = {
  telemetry_id: string
  ai_available?: boolean
  prediction?: PredictResponse
  incident?: IncidentListItem | null
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
        current_status: 'YENI',
        fault_type: prediction.fault_type,
        priority: prediction.priority,
        probability: prediction.probability,
        ai_suggestion: prediction.suggestion,
        assigned_team_name: null,
      }
    }
    return { telemetry_id, prediction, incident, ai_available: true }
  }

  const envelope = await apiFetch<TelemetryApiData>('/api/v1/telemetry', {
    method: 'POST',
    body: JSON.stringify(input),
    skipAuth: true,
  })

  const data = envelope.data
  if (!data) throw new Error('Telemetri cevabı boş')

  let prediction = data.prediction ?? null
  if (!prediction && data.incident) {
    prediction = predictionFromIncident(data.incident, input)
  }
  if (!prediction && data.ai_available === false) {
    prediction = {
      probability: 0,
      fault_type: FT.BELIRSIZ,
      priority: P.ORTA,
      suggestion: S.VAKA_AC,
      method: PredictionMethod.RULE_FALLBACK,
      confidence_explanation: 'AI Service ulaşılamadı — BELIRSIZ/ORTA ile vaka açıldı.',
    }
  }
  if (!prediction) {
    prediction = localPredict(input)
  }

  return {
    telemetry_id: data.telemetry_id,
    prediction,
    incident: data.incident ?? null,
    ai_available: data.ai_available,
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

  const body: Record<string, string> = { to_status: String(to_status) }
  if (resolution_note) body.note = resolution_note

  // X-User-* apiFetch tarafından auth mock iken enjekte edilir
  const envelope = await apiFetch<IncidentListItem>(`/api/v1/incidents/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!envelope.data) throw new Error('Durum güncelleme cevabı boş')
  return envelope.data
}

const mockMyIncidents: IncidentListItem[] = []

export async function reportIncident(description: string): Promise<IncidentListItem> {
  if (useIncidentMock()) {
    const item: IncidentListItem = {
      id: `mock-report-${Date.now()}`,
      incident_number: `INC-2026-${String(Date.now()).slice(-6)}`,
      station_code: 'MUSTERI-BILDIRIMI',
      current_status: 'YENI',
      fault_type: FT.BELIRSIZ,
      priority: P.ORTA,
      customer_description: description,
      created_at: new Date().toISOString(),
    }
    mockMyIncidents.unshift(item)
    return item
  }

  const envelope = await apiFetch<IncidentListItem>('/api/v1/incidents/report', {
    method: 'POST',
    body: JSON.stringify({ description }),
  })
  if (!envelope.data) throw new Error('Arıza bildirimi cevabı boş')
  return envelope.data
}

export async function listMyIncidents(): Promise<IncidentListItem[]> {
  if (useIncidentMock()) return mockMyIncidents

  const envelope = await apiFetch<IncidentListItem[]>('/api/v1/incidents/mine')
  return envelope.data ?? []
}

export function incidentModeLabel(): string {
  return useIncidentMock()
    ? `mock incident (${getApiBaseUrl()})`
    : `live incident (${getApiBaseUrl()})`
}

export type { ResponseEnvelope }
export { mockPredictSuccess }
