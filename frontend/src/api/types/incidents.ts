/** Incident list item — aligned with incident-service GET /incidents skeleton */

import type { FaultType, IncidentStatus, Priority } from './enums'

export interface IncidentListItem {
  id: string
  incident_number: string
  station_code: string
  current_status: IncidentStatus | string
  fault_type: FaultType | string | null
  priority: Priority | string | null
  assigned_team_name?: string | null
  sla_due_at?: string | null
}
