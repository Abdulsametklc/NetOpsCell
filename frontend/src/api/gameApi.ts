import type { GameProfile, LeaderboardEntry, LeaderboardPeriod } from './types'
import { apiFetch, getApiBaseUrl } from './client'
import { DEMO_USER_ID } from './mocks/auth'
import { mockLeaderboard, mockProfile } from './mocks/game'
import { useAuthStore } from '../store/authStore'

function useGameMock(): boolean {
  return import.meta.env.VITE_USE_GAME_MOCK === 'true'
}

export async function fetchLeaderboard(
  period: LeaderboardPeriod = 'daily',
  limit = 10,
): Promise<LeaderboardEntry[]> {
  if (useGameMock()) {
    return mockLeaderboard(period).slice(0, limit)
  }

  const envelope = await apiFetch<LeaderboardEntry[]>(
    `/api/v1/game/leaderboard?period=${period}&limit=${limit}`,
  )
  const rows = envelope.data ?? []
  return rows.map((r, i) => ({ ...r, rank: r.rank ?? i + 1 }))
}

export async function fetchGameProfile(userId?: string): Promise<GameProfile> {
  if (useGameMock()) {
    return mockProfile(userId ?? useAuthStore.getState().user?.id ?? DEMO_USER_ID)
  }

  // Backend iskelet: GET /profile/{user_id} ( /me henüz yok )
  const id = userId ?? useAuthStore.getState().user?.id ?? DEMO_USER_ID
  const envelope = await apiFetch<GameProfile>(`/api/v1/game/profile/${id}`)
  if (!envelope.data) throw new Error('Profil bulunamadı')
  return envelope.data
}

export function gameModeLabel(): string {
  return useGameMock()
    ? `mock game (${getApiBaseUrl()})`
    : `live game (${getApiBaseUrl()})`
}
