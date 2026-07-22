import type {
  AccuracyReport,
  AssignableTeam,
  AuditLogRow,
  CreatePersonnelRequest,
  NamedCount,
  StatsSummary,
  UnassignedIncident,
} from './types'
import { apiFetch, getApiBaseUrl } from './client'
import {
  mockAccuracy,
  mockAuditLogs,
  mockStatsSummary,
  mockTeams,
  mockUnassigned,
} from './mocks/dashboard'

function useDashMock(): boolean {
  return import.meta.env.VITE_USE_DASHBOARD_MOCK !== 'false'
}

/** incident-service'in gerçek /stats/summary cevabı — StatsSummary'den farklı
 * alan adları/şekiller kullanıyor (dict vs array). Bkz. StatsSummary adaptörü. */
interface RawStatsSummary {
  fault_type_distribution: Record<string, number>
  priority_distribution: Record<string, number>
  sla_compliance_rate: number | null
  sla_breached_active_count: number
  resolved_count: number
  avg_resolution_minutes: number | null
  unassigned_queue_count: number
}

function toNamedCounts(dist: Record<string, number>): NamedCount[] {
  return Object.entries(dist).map(([name, count]) => ({ name, count }))
}

function adaptStatsSummary(raw: RawStatsSummary): StatsSummary {
  return {
    by_fault_type: toNamedCounts(raw.fault_type_distribution ?? {}),
    by_priority: toNamedCounts(raw.priority_distribution ?? {}),
    // incident-service henüz günlük trend agregasyonu üretmiyor - boş dizi güvenli varsayılan.
    priority_trend: [],
    sla_compliance_pct: raw.sla_compliance_rate ?? 0,
    sla_breached_active: raw.sla_breached_active_count ?? 0,
    // incident-service henüz ekip bazlı kırılım üretmiyor - boş dizi güvenli varsayılan.
    teams: [],
  }
}

/** ai-service'in gerçek /accuracy cevabı — AccuracyReport'tan farklı alan
 * adları/şekiller kullanıyor (dict vs array, "accuracy_rate" vs "overall_pct"). */
interface RawAccuracyCategory {
  total_evaluated: number
  incorrect_count: number
  accuracy_rate: number | null
}

interface RawAccuracy {
  total_evaluated: number
  incorrect_count: number
  accuracy_rate: number | null
  by_category?: Record<string, RawAccuracyCategory>
}

function adaptAccuracy(raw: RawAccuracy): AccuracyReport {
  const by_category = Object.entries(raw.by_category ?? {}).map(([category, v]) => ({
    category,
    correct: v.total_evaluated - v.incorrect_count,
    total: v.total_evaluated,
    pct: v.accuracy_rate ?? 0,
  }))
  return {
    overall_pct: raw.accuracy_rate ?? 0,
    // ai-service şu an ayrı bir "false alarm" sayacı tutmuyor - güvenli varsayılan.
    false_alarms: 0,
    by_category,
  }
}

export async function fetchStatsSummary(): Promise<StatsSummary> {
  if (useDashMock()) return mockStatsSummary
  const envelope = await apiFetch<RawStatsSummary>('/api/v1/incidents/stats/summary')
  if (!envelope.data) throw new Error('Stats boş')
  return adaptStatsSummary(envelope.data)
}

export async function fetchAccuracy(): Promise<AccuracyReport> {
  if (useDashMock()) return mockAccuracy
  const envelope = await apiFetch<RawAccuracy>(
    '/api/v1/ai/accuracy?breakdown=category',
  )
  if (!envelope.data) throw new Error('Accuracy boş')
  return adaptAccuracy(envelope.data)
}

export async function fetchUnassignedQueue(): Promise<UnassignedIncident[]> {
  if (useDashMock()) return [...mockUnassigned]
  const envelope = await apiFetch<UnassignedIncident[]>(
    '/api/v1/incidents/queue/unassigned',
  )
  return envelope.data ?? []
}

export async function fetchAssignableTeams(): Promise<AssignableTeam[]> {
  if (useDashMock()) return mockTeams
  const envelope = await apiFetch<AssignableTeam[]>('/api/v1/ai/teams')
  return envelope.data ?? []
}

export async function assignIncident(
  incidentId: string,
  teamId: string,
  teamName: string,
): Promise<void> {
  if (useDashMock()) {
    const idx = mockUnassigned.findIndex((i) => i.id === incidentId)
    if (idx >= 0) mockUnassigned.splice(idx, 1)
    void teamId
    return
  }
  // incident-service kendi DB'sinde ekip adi tutmuyor (database-per-service) - bu yuzden
  // manuel atamada team_name'i de birlikte gondermemiz gerekiyor (bkz. ManualAssignRequest).
  await apiFetch(`/api/v1/incidents/${incidentId}/assign`, {
    method: 'PATCH',
    body: JSON.stringify({ team_id: teamId, team_name: teamName }),
  })
}

export async function fetchAuditLogs(): Promise<AuditLogRow[]> {
  if (useDashMock()) return mockAuditLogs
  const envelope = await apiFetch<AuditLogRow[]>('/api/v1/auth/audit-logs')
  return envelope.data ?? []
}

export async function createPersonnel(body: CreatePersonnelRequest): Promise<void> {
  if (useDashMock()) {
    // Demo: sadece başarılı say
    await new Promise((r) => setTimeout(r, 400))
    return
  }
  await apiFetch('/api/v1/auth/personnel', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function dashboardModeLabel(): string {
  return useDashMock()
    ? `mock dashboard (${getApiBaseUrl()})`
    : `live dashboard (${getApiBaseUrl()})`
}
