import { useEffect, useState } from 'react'
import type { GameProfile } from '../api/types'
import { fetchGameProfile, gameModeLabel } from '../api/gameApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
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
    <AppShell title="NetOpsCell — Profil" subtitle={gameModeLabel()}>
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && !profile && <EmptyState message="Profil bulunamadı." />}
      {!loading && !error && profile && (
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
            <h2 className="text-xl font-medium">
              {profile.display_name ?? authUser?.first_name ?? 'Operatör'}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Seviye <span className="text-amber-300">{profile.level}</span>
              {profile.rank != null && (
                <>
                  {' '}
                  · Sıra <span className="text-sky-300">#{profile.rank}</span>
                </>
              )}
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 text-sm">
              <div>
                <dt className="text-slate-500">Toplam puan</dt>
                <dd className="text-lg font-mono text-sky-300">{profile.total_points}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Çözülen vaka</dt>
                <dd className="text-lg font-mono">{profile.resolved_count}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Ort. puan</dt>
                <dd className="text-lg font-mono">{profile.avg_points.toFixed(1)}</dd>
              </div>
            </dl>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">
              Rozetler
            </h3>
            {!profile.badges?.length ? (
              <EmptyState message="Henüz rozet yok." />
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {profile.badges.map((b) => (
                  <li
                    key={b.code}
                    className={`rounded-lg border p-4 text-sm ${
                      b.earned_at
                        ? 'border-amber-700/50 bg-amber-950/30'
                        : 'border-slate-800 bg-slate-900/30 opacity-60'
                    }`}
                  >
                    <p className="font-medium text-amber-200">{b.name}</p>
                    <p className="mt-1 text-xs text-slate-400">{b.description}</p>
                    <p className="mt-2 text-xs text-slate-500">
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
