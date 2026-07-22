/** Mirrors docs/CONTRACTS.md §2.3 */

import type { FaultType, Priority } from './enums'

export interface AssignRequest {
  incident_id: string
  incident_number: string
  fault_type: FaultType
  priority: Priority
  lat: number
  lng: number
}

export interface ScoreComponents {
  uzmanlik_eslesme: number
  mesafe_yakinlik: number
  bosluk_orani: number
}

export interface AssignResponse {
  queued: boolean
  team_id?: string | null
  team_name?: string | null
  score?: number | null
  components?: ScoreComponents | null
}
