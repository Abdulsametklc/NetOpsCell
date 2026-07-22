import type {
  AccuracyReport,
  AssignableTeam,
  AuditLogRow,
  StatsSummary,
  UnassignedIncident,
} from '../types'

export const mockStatsSummary: StatsSummary = {
  by_fault_type: [
    { name: 'ISINMA', count: 14 },
    { name: 'DONANIM', count: 11 },
    { name: 'BAGLANTI', count: 9 },
    { name: 'GUC_KESINTISI', count: 6 },
    { name: 'YAZILIM', count: 4 },
    { name: 'BELIRSIZ', count: 3 },
  ],
  by_priority: [
    { name: 'KRITIK', count: 5 },
    { name: 'YUKSEK', count: 12 },
    { name: 'ORTA', count: 18 },
    { name: 'DUSUK', count: 12 },
  ],
  priority_trend: [
    { day: 'Pzt', DUSUK: 2, ORTA: 3, YUKSEK: 2, KRITIK: 1 },
    { day: 'Sal', DUSUK: 1, ORTA: 4, YUKSEK: 3, KRITIK: 0 },
    { day: 'Çar', DUSUK: 3, ORTA: 2, YUKSEK: 2, KRITIK: 2 },
    { day: 'Per', DUSUK: 2, ORTA: 5, YUKSEK: 1, KRITIK: 1 },
    { day: 'Cum', DUSUK: 1, ORTA: 3, YUKSEK: 4, KRITIK: 1 },
    { day: 'Cmt', DUSUK: 2, ORTA: 1, YUKSEK: 1, KRITIK: 0 },
    { day: 'Paz', DUSUK: 1, ORTA: 2, YUKSEK: 1, KRITIK: 0 },
  ],
  sla_compliance_pct: 86.4,
  sla_breached_active: 3,
  teams: [
    { team_id: 't1', team_name: 'IST-AVRUPA-A', resolved: 22, avg_minutes: 48, reopen_rate: 0.09 },
    { team_id: 't2', team_name: 'IST-ANADOLU-B', resolved: 17, avg_minutes: 61, reopen_rate: 0.12 },
    { team_id: 't3', team_name: 'ANK-MERKEZ', resolved: 14, avg_minutes: 55, reopen_rate: 0.07 },
  ],
}

export const mockAccuracy: AccuracyReport = {
  overall_pct: 78.5,
  false_alarms: 6,
  by_category: [
    { category: 'ISINMA', correct: 18, total: 22, pct: 81.8 },
    { category: 'DONANIM', correct: 14, total: 19, pct: 73.7 },
    { category: 'BAGLANTI', correct: 12, total: 15, pct: 80.0 },
    { category: 'GUC_KESINTISI', correct: 9, total: 11, pct: 81.8 },
    { category: 'YAZILIM', correct: 5, total: 8, pct: 62.5 },
  ],
}

export const mockUnassigned: UnassignedIncident[] = [
  {
    id: 'u1',
    incident_number: 'INC-2026-000210',
    station_code: 'IST-AVR-055',
    fault_type: 'BELIRSIZ',
    priority: 'ORTA',
    created_at: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
  },
  {
    id: 'u2',
    incident_number: 'INC-2026-000214',
    station_code: 'IST-ANAD-012',
    fault_type: 'BAGLANTI',
    priority: 'YUKSEK',
    created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
  },
]

export const mockTeams: AssignableTeam[] = [
  { team_id: 't1', team_name: 'IST-AVRUPA-A', active_load: 2 },
  { team_id: 't2', team_name: 'IST-ANADOLU-B', active_load: 1 },
  { team_id: 't3', team_name: 'ANK-MERKEZ', active_load: 3 },
]

export const mockAuditLogs: AuditLogRow[] = [
  {
    id: 'a1',
    user_id: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
    action_type: 'LOGIN_SUCCESS',
    resource_type: 'auth',
    resource_id: null,
    result: 'SUCCESS',
    ip_address: '10.0.0.12',
    created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
  },
  {
    id: 'a2',
    user_id: null,
    action_type: 'LOGIN_FAILURE',
    resource_type: 'auth',
    resource_id: null,
    result: 'FAILURE',
    ip_address: '185.2.3.4',
    created_at: new Date(Date.now() - 55 * 60 * 1000).toISOString(),
  },
  {
    id: 'a3',
    user_id: 'admin-1',
    action_type: 'ROLE_CHANGED',
    resource_type: 'user',
    resource_id: 'tech-9',
    result: 'SUCCESS',
    ip_address: '10.0.0.2',
    created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
  },
]
