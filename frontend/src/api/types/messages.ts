import type { Role } from './auth'

export interface IncidentMessage {
  id: string
  incident_id: string
  sender_id: string
  sender_role: Role | string
  sender_name?: string
  content: string
  created_at: string
}

export interface PostMessageRequest {
  content: string
}
