import type { IncidentListItem } from '../types'
import { FaultType, IncidentStatus, Priority } from '../types'

/** CP2: teknisyen dashboard mock — CP3'te gerçek API'ye geçilir */
export const mockAssignedIncidents: IncidentListItem[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    incident_number: 'INC-2026-000101',
    station_code: 'IST-AVR-042',
    current_status: IncidentStatus.ATANDI,
    fault_type: FaultType.ISINMA,
    priority: Priority.KRITIK,
    assigned_team_name: 'IST-AVRUPA-A',
    sla_due_at: new Date(Date.now() + 45 * 60 * 1000).toISOString(),
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    incident_number: 'INC-2026-000098',
    station_code: 'IST-AVR-017',
    current_status: IncidentStatus.YOLDA,
    fault_type: FaultType.DONANIM,
    priority: Priority.YUKSEK,
    assigned_team_name: 'IST-AVRUPA-A',
    sla_due_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    incident_number: 'INC-2026-000090',
    station_code: 'IST-ANAD-003',
    current_status: IncidentStatus.MUDAHALE_EDILIYOR,
    fault_type: FaultType.BAGLANTI,
    priority: Priority.ORTA,
    assigned_team_name: 'IST-AVRUPA-A',
    sla_due_at: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
  },
]
