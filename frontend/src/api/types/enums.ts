/** Mirrors docs/CONTRACTS.md §1 */

export const FaultType = {
  DONANIM: 'DONANIM',
  GUC_KESINTISI: 'GUC_KESINTISI',
  BAGLANTI: 'BAGLANTI',
  YAZILIM: 'YAZILIM',
  ISINMA: 'ISINMA',
  BELIRSIZ: 'BELIRSIZ',
} as const
export type FaultType = (typeof FaultType)[keyof typeof FaultType]

export const Priority = {
  DUSUK: 'DUSUK',
  ORTA: 'ORTA',
  YUKSEK: 'YUKSEK',
  KRITIK: 'KRITIK',
} as const
export type Priority = (typeof Priority)[keyof typeof Priority]

export const Suggestion = {
  IZLE: 'IZLE',
  VAKA_AC: 'VAKA_AC',
  ACIL: 'ACIL',
} as const
export type Suggestion = (typeof Suggestion)[keyof typeof Suggestion]

export const IncidentStatus = {
  YENI: 'YENI',
  ATANDI: 'ATANDI',
  YOLDA: 'YOLDA',
  MUDAHALE_EDILIYOR: 'MUDAHALE_EDILIYOR',
  PARCA_BEKLENIYOR: 'PARCA_BEKLENIYOR',
  COZULDU: 'COZULDU',
  KAPANDI: 'KAPANDI',
} as const
export type IncidentStatus = (typeof IncidentStatus)[keyof typeof IncidentStatus]

export const PowerStatus = {
  NORMAL: 'NORMAL',
  KESINTIDE: 'KESINTIDE',
} as const
export type PowerStatus = (typeof PowerStatus)[keyof typeof PowerStatus]

export const PredictionMethod = {
  LLM: 'LLM',
  RULE_FALLBACK: 'RULE_FALLBACK',
} as const
export type PredictionMethod = (typeof PredictionMethod)[keyof typeof PredictionMethod]
