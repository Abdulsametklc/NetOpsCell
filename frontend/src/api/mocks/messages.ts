import type { IncidentMessage } from '../types'

const store = new Map<string, IncidentMessage[]>()

function seed(incidentId: string): IncidentMessage[] {
  if (!store.has(incidentId)) {
    store.set(incidentId, [
      {
        id: `msg-${incidentId}-1`,
        incident_id: incidentId,
        sender_id: 'noc-1',
        sender_role: 'NOC_OPERATORU',
        sender_name: 'NOC Operatör',
        content: 'İstasyona yaklaşırken termal kamera hazır olsun.',
        created_at: new Date(Date.now() - 40 * 60 * 1000).toISOString(),
      },
      {
        id: `msg-${incidentId}-2`,
        incident_id: incidentId,
        sender_id: 'mock-user-1',
        sender_role: 'SAHA_TEKNISYENI',
        sender_name: 'Demo Teknisyen',
        content: 'Yoldayım, 15 dk içinde sahadayım.',
        created_at: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
      },
    ])
  }
  return store.get(incidentId)!
}

export function mockListMessages(incidentId: string): IncidentMessage[] {
  return [...seed(incidentId)]
}

export function mockPostMessage(
  incidentId: string,
  content: string,
  sender: { id: string; role: string; name?: string },
): IncidentMessage {
  const list = seed(incidentId)
  const msg: IncidentMessage = {
    id: `msg-${incidentId}-${Date.now()}`,
    incident_id: incidentId,
    sender_id: sender.id,
    sender_role: sender.role,
    sender_name: sender.name,
    content,
    created_at: new Date().toISOString(),
  }
  list.push(msg)
  return msg
}
