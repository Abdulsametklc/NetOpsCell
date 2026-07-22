/** Mirrors docs/CONTRACTS.md §3 — WS / Notification Hub payloads */

import type {
  FaultType,
  IncidentStatus,
  PredictionMethod,
  Priority,
  Suggestion,
} from './enums'

export interface IdentityPersonnelUpserted {
  event_type: 'identity.personnel.upserted'
  user_id: string
  name: string
  specializations: FaultType[]
  regions: string[]
  base_lat: number
  base_lon: number
  is_active: boolean
}

export interface AiPredictionCompleted {
  event_type: 'ai.prediction.completed'
  telemetry_id: string
  probability: number
  fault_type: FaultType
  priority: Priority
  suggestion: Suggestion
  method: PredictionMethod
}

export interface IncidentCreated {
  event_type: 'incident.created'
  incident_id: string
  incident_number: string
  station_code: string
  fault_type: FaultType
  priority: Priority
  probability: number
  created_at: string
}

export interface IncidentAssigned {
  event_type: 'incident.assigned'
  incident_id: string
  team_id: string
  team_name: string
  score: number
  assigned_by: string
  assigned_at: string
}

export interface IncidentStatusChanged {
  event_type: 'incident.status_changed'
  incident_id: string
  from_status: IncidentStatus
  to_status: IncidentStatus
  changed_by: string
  changed_at: string
}

export interface IncidentTypeChanged {
  event_type: 'incident.type_changed'
  incident_id: string
  original_fault_type: FaultType
  new_fault_type: FaultType
  changed_by: string
  changed_at: string
}

export interface IncidentPriorityChanged {
  event_type: 'incident.priority_changed'
  incident_id: string
  original_priority: Priority
  new_priority: Priority
  changed_by: string
  changed_at: string
}

export interface IncidentPartFulfilled {
  event_type: 'incident.part.fulfilled'
  incident_id: string
  fulfilled_by: string
  fulfilled_at: string
}

export interface IncidentSlaBreached {
  event_type: 'incident.sla_breached'
  incident_id: string
  priority: Priority
  sla_due_at: string
  breached_at: string
}

export interface IncidentResolved {
  event_type: 'incident.resolved'
  incident_id: string
  team_id: string
  fault_type: FaultType
  priority: Priority
  created_at: string
  resolved_at: string
}

export interface IncidentEvaluated {
  event_type: 'incident.evaluated'
  incident_id: string
  stars: number
  is_permanent: boolean
  evaluated_by: string
}

export interface GamePointsAwarded {
  event_type: 'game.points_awarded'
  user_id: string
  incident_id: string | null
  points: number
  reason: string
  new_total: number
}

export interface BadgeEarned {
  event_type: 'badge.earned'
  user_id: string
  badge_code: string
  earned_at: string
}

export type NotificationEvent =
  | IdentityPersonnelUpserted
  | AiPredictionCompleted
  | IncidentCreated
  | IncidentAssigned
  | IncidentStatusChanged
  | IncidentTypeChanged
  | IncidentPriorityChanged
  | IncidentPartFulfilled
  | IncidentSlaBreached
  | IncidentResolved
  | IncidentEvaluated
  | GamePointsAwarded
  | BadgeEarned
