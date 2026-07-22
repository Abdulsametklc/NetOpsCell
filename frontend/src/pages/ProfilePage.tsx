import { useEffect, useState } from 'react'
import type { GameProfile } from '../api/types'
import { fetchGameProfile } from '../api/gameApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
import { Card } from '../components/ui'
import { useAuthStore } from '../store/authStore'

export function ProfilePage() {
  const authUser = useAuthStore((s) => s.user)
  const [profile, setProfile] = useState<GameProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchGameProfile(authUser?.id)
        if (!cancelled) setProfile(data)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError || err instanceof Error ? err.message : 'Profil alınamadı')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [authUser?.id])

  return (
    <AppShell title="NetOpsCell — Profil">
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && !profile && <EmptyState message="Profil bulunamadı." />}
      {!loading && !error && profile && (
        <div className="space-y-6">
          <Card className="bg-gradient-to-br from-tc-navy-900 to-tc-navy-800 p-6 text-white dark:border-tc-navy-700">
            <h2 className="text-xl font-semibold">
              {profile.display_name ?? authUser?.first_name ?? 'Operatör'}
            </h2>
            <p className="mt-1 text-sm text-white/70">
              Seviye <span className="font-semibold text-tc-yellow-400">{profile.level}</span>
              {profile.rank != null && (
                <>
                  {' '}
                  · Sıra <span className="font-semibold text-white">#{profile.rank}</span>
                </>
              )}
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-white/50">Toplam puan</dt>
                <dd className="font-mono text-lg font-semibold text-tc-yellow-400">{profile.total_points}</dd>
              </div>
              <div>
                <dt className="text-white/50">Çözülen vaka</dt>
                <dd className="font-mono text-lg">{profile.resolved_count}</dd>
              </div>
              <div>
                <dt className="text-white/50">Ort. puan</dt>
                <dd className="font-mono text-lg">{profile.avg_points.toFixed(1)}</dd>
              </div>
            </dl>
          </Card>

          <section>
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Rozetler
            </h3>
            {!profile.badges?.length ? (
              <EmptyState message="Henüz rozet yok." />
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {profile.badges.map((b) => (
                  <li
                    key={b.code}
                    className={`rounded-xl border p-4 text-sm ${
                      b.earned_at
                        ? 'border-tc-yellow-400/60 bg-tc-yellow-50 dark:border-tc-yellow-600/40 dark:bg-tc-yellow-500/10'
                        : 'border-slate-200 bg-slate-50 opacity-60 dark:border-tc-navy-800 dark:bg-tc-navy-900/30'
                    }`}
                  >
                    <p className="font-semibold text-tc-navy-900 dark:text-tc-yellow-200">{b.name}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{b.description}</p>
                    <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
                      {b.earned_at
                        ? `Kazanıldı: ${new Date(b.earned_at).toLocaleDateString('tr-TR')}`
                        : 'Henüz kazanılmadı'}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </AppShell>
  )
}
