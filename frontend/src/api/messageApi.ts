import type { IncidentMessage } from './types'
import { apiFetch, getApiBaseUrl } from './client'
import { mockListMessages, mockPostMessage } from './mocks/messages'
import { useAuthStore } from '../store/authStore'

function useMessageMock(): boolean {
  // Endpoint CP5 Kişi 2'de; gelene kadar varsayılan mock
  const explicit = import.meta.env.VITE_USE_MESSAGE_MOCK as string | undefined
  if (explicit === 'false') return false
  return true
}

export async function listMessages(incidentId: string): Promise<IncidentMessage[]> {
  if (useMessageMock()) return mockListMessages(incidentId)

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
  if (useMessageMock()) {
    return mockPostMessage(incidentId, content, {
      id: user?.id ?? 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
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
  return useMessageMock()
    ? `mock messages (${getApiBaseUrl()})`
    : `live messages (${getApiBaseUrl()})`
}
