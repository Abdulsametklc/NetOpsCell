import type { IncidentMessage } from './types'
import { apiFetch, getApiBaseUrl } from './client'
import { mockListMessages, mockPostMessage } from './mocks/messages'
import { useAuthStore } from '../store/authStore'

function useIncidentMock(): boolean {
  return import.meta.env.VITE_USE_INCIDENT_MOCK === 'true'
}

export async function listMessages(incidentId: string): Promise<IncidentMessage[]> {
  if (useIncidentMock()) return mockListMessages(incidentId)

  const envelope = await apiFetch<IncidentMessage[]>(
    `/api/v1/incidents/${incidentId}/messages`,
  )
  return envelope.data ?? []
}

export async function postMessage(
  incidentId: string,
  content: string,
): Promise<IncidentMessage> {
  const user = useAuthStore.getState().user
  if (useIncidentMock()) {
    return mockPostMessage(incidentId, content, {
      id: user?.id ?? 'mock-user-1',
      role: String(user?.role ?? 'SAHA_TEKNISYENI'),
      name: user?.first_name ?? 'Operatör',
    })
  }

  const envelope = await apiFetch<IncidentMessage>(
    `/api/v1/incidents/${incidentId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({ content }),
    },
  )
  if (!envelope.data) throw new Error('Mesaj gönderilemedi')
  return envelope.data
}

export function messagesModeLabel(): string {
  return useIncidentMock()
    ? `mock messages (${getApiBaseUrl()})`
    : `live messages (${getApiBaseUrl()})`
}
