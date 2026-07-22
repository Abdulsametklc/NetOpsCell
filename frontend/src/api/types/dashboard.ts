/** CP6 süpervizör dashboard + admin — ARCHITECTURE §10 */

export interface NamedCount {
  name: string
  count: number
}

export interface PriorityTrendPoint {
  day: string
  DUSUK: number
  ORTA: number
  YUKSEK: number
  KRITIK: number
}

export interface TeamPerformanceRow {
  team_id: string
  team_name: string
  resolved: number
  avg_minutes: number
  reopen_rate: number
}

export interface StatsSummary {
  by_fault_type: NamedCount[]
  by_priority: NamedCount[]
  priority_trend: PriorityTrendPoint[]
  sla_compliance_pct: number
  sla_breached_active: number
  teams: TeamPerformanceRow[]
}

export interface AccuracyBreakdown {
  category: string
  correct: number
  total: number
  pct: number
}

export interface AccuracyReport {
  overall_pct: number
  false_alarms: number
  by_category: AccuracyBreakdown[]
}

export interface UnassignedIncident {
  id: string
  incident_number: string
  station_code: string
  fault_type: string | null
  priority: string | null
  created_at?: string | null
}

export interface AssignableTeam {
  team_id: string
  team_name: string
  active_load: number
}

export interface AuditLogRow {
  id: string
  user_id: string | null
  action_type: string
  resource_type: string | null
  resource_id: string | null
  result: string
  ip_address: string | null
  created_at: string
}

export interface CreatePersonnelRequest {
  email: string
  password: string
  first_name: string
  last_name: string
  role: string
  specializations: string[]
  regions: string[]
  base_lat?: number
  base_lon?: number
}
