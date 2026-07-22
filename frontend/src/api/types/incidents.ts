/** Incident list/detail — incident-service _incident_summary ile hizalı */

import type { FaultType, IncidentStatus, Priority, Suggestion } from './enums'

export interface IncidentListItem {
  id: string
  incident_number: string
  station_code: string
  current_status: IncidentStatus | string
  fault_type: FaultType | string | null
  priority: Priority | string | null
  probability?: number | null
  ai_suggestion?: Suggestion | string | null
  assigned_team_id?: string | null
  assigned_team_name?: string | null
  created_at?: string | null
  sla_due_at?: string | null
  sla_status?: 'ACTIVE' | 'MET' | 'BREACHED' | string | null
}
