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

/**
 * incident-service/app/core/state_machine.py ile birebir aynı yetki kuralları:
 * - SAHA_TEKNISYENI: sadece KENDİNE atanan vakada teknisyen geçişleri
 * - NOC_OPERATORU: sadece COZULDU -> KAPANDI
 * - SUPERVIZOR / ADMIN: PATCH /status üzerinden hiçbir geçiş yapamaz (manuel atama
 *   ayrı bir uçtur, ARCHITECTURE.md §3.1 - "Durum değiştirme" sütununda Admin ✗)
 */
export function allowedNextStatuses(
  current: string,
  role: Role | string | null | undefined,
  isAssignedToMe: boolean,
): string[] {
  if (role === 'SAHA_TEKNISYENI') {
    return isAssignedToMe ? (TECH_TRANSITIONS[current] ?? []) : []
  }
  if (role === 'NOC_OPERATORU') {
    return NOC_TRANSITIONS[current] ?? []
  }
  return []
}

export function statusActionLabel(to: string): string {
  return LABEL[to] ?? to
}

export function requiresResolutionNote(to: string): boolean {
  return to === IncidentStatus.COZULDU
}
