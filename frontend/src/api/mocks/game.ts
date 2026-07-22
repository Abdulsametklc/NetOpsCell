import type { GameProfile, LeaderboardEntry, LeaderboardPeriod } from '../types'
import { Level } from '../types'

const NAMES = [
  'Ayşe Yılmaz',
  'Mehmet Demir',
  'Zeynep Kaya',
  'Demo Teknisyen',
  'Can Öztürk',
  'Elif Şahin',
  'Burak Arslan',
  'Selin Aydın',
  'Emre Çelik',
  'Deniz Koç',
]

function pointsFor(period: LeaderboardPeriod, seed: number): number {
  const base = period === 'daily' ? 18 : 95
  return base + ((seed * 17) % 40)
}

export function mockLeaderboard(period: LeaderboardPeriod): LeaderboardEntry[] {
  return NAMES.map((display_name, i) => ({
    user_id: `user-${i + 1}`,
    display_name,
    points: pointsFor(period, i + 1),
    level: i < 2 ? Level.ALTIN : i < 5 ? Level.GUMUS : Level.BRONZ,
    rank: i + 1,
  })).sort((a, b) => b.points - a.points)
    .map((e, i) => ({ ...e, rank: i + 1 }))
}

export function mockProfile(userId = 'mock-user-1'): GameProfile {
  return {
    user_id: userId,
    display_name: 'Demo Teknisyen',
    total_points: 128,
    level: Level.GUMUS,
    resolved_count: 11,
    avg_points: 11.6,
    rank: 4,
    badges: [
      {
        code: 'ILK_MUDAHALE',
        name: 'İlk Müdahale',
        description: 'İlk arızayı çözdün',
        earned_at: new Date(Date.now() - 86400000 * 3).toISOString(),
      },
      {
        code: 'HIZ_USTASI',
        name: 'Hız Ustası',
        description: 'SLA yarısında 10 müdahale',
        earned_at: null,
      },
    ],
  }
}
