import type {
  AccuracyReport,
  AssignableTeam,
  AuditLogRow,
  CreatePersonnelRequest,
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

export async function fetchStatsSummary(): Promise<StatsSummary> {
  if (useDashMock()) return mockStatsSummary
  const envelope = await apiFetch<StatsSummary>('/api/v1/incidents/stats/summary')
  if (!envelope.data) throw new Error('Stats boş')
  return envelope.data
}

export async function fetchAccuracy(): Promise<AccuracyReport> {
  if (useDashMock()) return mockAccuracy
  const envelope = await apiFetch<AccuracyReport>(
    '/api/v1/ai/accuracy?breakdown=category',
  )
  if (!envelope.data) throw new Error('Accuracy boş')
  return envelope.data
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
): Promise<void> {
  if (useDashMock()) {
    const idx = mockUnassigned.findIndex((i) => i.id === incidentId)
    if (idx >= 0) mockUnassigned.splice(idx, 1)
    void teamId
    return
  }
  await apiFetch(`/api/v1/incidents/${incidentId}/assign`, {
    method: 'PATCH',
    body: JSON.stringify({ team_id: teamId }),
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
