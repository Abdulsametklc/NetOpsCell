/** Gamification — ARCHITECTURE.md §4.4 */

export const Level = {
  BRONZ: 'BRONZ',
  GUMUS: 'GUMUS',
  ALTIN: 'ALTIN',
  PLATIN: 'PLATIN',
} as const
export type Level = (typeof Level)[keyof typeof Level]

export type LeaderboardPeriod = 'daily' | 'weekly'

export interface LeaderboardEntry {
  user_id: string
  display_name?: string
  points: number
  level?: Level | string
  rank?: number
}

export interface BadgeInfo {
  code: string
  name: string
  description: string
  earned_at?: string | null
}

export interface GameProfile {
  user_id: string
  display_name?: string
  total_points: number
  level: Level | string
  resolved_count: number
  avg_points: number
  rank?: number | null
  badges?: BadgeInfo[]
}

export type ToastKind = 'info' | 'success' | 'badge' | 'warning'

export interface AppToast {
  id: string
  kind: ToastKind
  title: string
  message?: string
}
