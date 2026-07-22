import type { GameProfile, LeaderboardEntry, LeaderboardPeriod } from './types'
import { apiFetch, getApiBaseUrl } from './client'
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
    return mockProfile(userId ?? useAuthStore.getState().user?.id ?? 'mock-user-1')
  }

  const id = userId ?? 'me'
  const path =
    id === 'me'
      ? '/api/v1/game/profile/me'
      : `/api/v1/game/profile/${id}`
  const envelope = await apiFetch<GameProfile>(path)
  if (!envelope.data) throw new Error('Profil bulunamadı')
  return envelope.data
}

export function gameModeLabel(): string {
  return useGameMock()
    ? `mock game (${getApiBaseUrl()})`
    : `live API (${getApiBaseUrl()})`
}
