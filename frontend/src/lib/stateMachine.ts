import { IncidentStatus } from '../api/types'
import type { Role } from '../api/types'

/** ARCHITECTURE.md §4.2.1 — teknisyen için geçerli geçişler */
const TECH_TRANSITIONS: Record<string, string[]> = {
  [IncidentStatus.ATANDI]: [IncidentStatus.YOLDA],
  [IncidentStatus.YOLDA]: [IncidentStatus.MUDAHALE_EDILIYOR],
  [IncidentStatus.MUDAHALE_EDILIYOR]: [
    IncidentStatus.PARCA_BEKLENIYOR,
    IncidentStatus.COZULDU,
  ],
  [IncidentStatus.PARCA_BEKLENIYOR]: [], // parça tedariki sistem; teknisyen bekler
}

const NOC_TRANSITIONS: Record<string, string[]> = {
  [IncidentStatus.COZULDU]: [IncidentStatus.KAPANDI],
}

const LABEL: Record<string, string> = {
  [IncidentStatus.YOLDA]: 'Sahaya çık (YOLDA)',
  [IncidentStatus.MUDAHALE_EDILIYOR]: 'Müdahaleye başla',
  [IncidentStatus.PARCA_BEKLENIYOR]: 'Parça bekleniyor',
  [IncidentStatus.COZULDU]: 'Çözüldü olarak işaretle',
  [IncidentStatus.KAPANDI]: 'Vakayı kapat',
}

export function allowedNextStatuses(
  current: string,
  role: Role | string | null | undefined,
): string[] {
  if (role === 'SAHA_TEKNISYENI') {
    return TECH_TRANSITIONS[current] ?? []
  }
  if (role === 'NOC_OPERATORU' || role === 'SUPERVIZOR' || role === 'ADMIN') {
    const tech = TECH_TRANSITIONS[current] ?? []
    const noc = NOC_TRANSITIONS[current] ?? []
    return [...new Set([...tech, ...noc])]
  }
  return []
}

export function statusActionLabel(to: string): string {
  return LABEL[to] ?? to
}

export function requiresResolutionNote(to: string): boolean {
  return to === IncidentStatus.COZULDU
}
