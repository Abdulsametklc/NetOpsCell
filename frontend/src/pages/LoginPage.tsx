import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { authModeLabel, fetchMe, login } from '../api/authApi'
import { useAuthStore } from '../store/authStore'
import { homePathForRole } from '../lib/roleRoutes'

type Tab = 'personnel' | 'customer'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const accessToken = useAuthStore((s) => s.accessToken)
  const role = useAuthStore((s) => s.user?.role)

  const [tab, setTab] = useState<Tab>('personnel')
  const [email, setEmail] = useState('teknisyen@netopscell.demo')
  const [password, setPassword] = useState('')
  const [gsm, setGsm] = useState('5551234567')
  const [otp, setOtp] = useState('1234')
  const [error, setError] = useState<string | null>(null)
  const [lockedHint, setLockedHint] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (accessToken) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from ?? homePathForRole(role)} replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLockedHint(null)
    setSubmitting(true)
    try {
      await login(
        tab === 'personnel'
          ? { email: email.trim(), password }
          : { gsm: gsm.trim(), otp: otp.trim() },
      )
      try {
        await fetchMe()
      } catch {
        /* JWT claim'leri yeterli */
      }
      const nextRole = useAuthStore.getState().user?.role
      const from = (location.state as { from?: string } | null)?.from
      navigate(from ?? homePathForRole(nextRole), { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        const code = err.envelope?.error?.code
        if (code === 'ACCOUNT_LOCKED') {
          const sec = err.envelope?.error?.retry_after_seconds
          setLockedHint(
            sec
              ? `Hesap kilitli. ${sec} sn sonra tekrar deneyin.`
              : 'Hesap kilitli. Daha sonra tekrar deneyin.',
          )
        }
        setError(err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Giriş başarısız')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">NetOpsCell</h1>
        <p className="text-slate-400 text-sm mb-6">Giriş — {authModeLabel()}</p>

        <div className="flex gap-2 mb-4">
          <button
            type="button"
            className={`flex-1 rounded px-3 py-2 text-sm ${
              tab === 'personnel' ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-300'
            }`}
            onClick={() => setTab('personnel')}
          >
            Personel
          </button>
          <button
            type="button"
            className={`flex-1 rounded px-3 py-2 text-sm ${
              tab === 'customer' ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-300'
            }`}
            onClick={() => setTab('customer')}
          >
            Müşteri (GSM+OTP)
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-5">
          {tab === 'personnel' ? (
            <>
              <label className="block text-sm">
                <span className="text-slate-400">E-posta</span>
                <input
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="text-slate-400">Şifre</span>
                <input
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required={!import.meta.env.VITE_USE_AUTH_MOCK}
                />
                {import.meta.env.VITE_USE_AUTH_MOCK === 'true' && (
                  <span className="mt-1 block text-xs text-slate-500">
                    Mock: şifre serbest. Rol için e-postada admin/noc/super kullan.
                  </span>
                )}
              </label>
            </>
          ) : (
            <>
              <label className="block text-sm">
                <span className="text-slate-400">GSM</span>
                <input
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  inputMode="tel"
                  value={gsm}
                  onChange={(e) => setGsm(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="text-slate-400">OTP</span>
                <input
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  required
                />
                <span className="mt-1 block text-xs text-slate-500">Simülasyon kodu: 1234</span>
              </label>
            </>
          )}

          {error && (
            <p className="text-sm text-rose-400" role="alert">
              {error}
            </p>
          )}
          {lockedHint && (
            <p className="text-sm text-amber-400" role="status">
              {lockedHint}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-sky-600 py-2.5 text-sm font-medium hover:bg-sky-500 disabled:opacity-60"
          >
            {submitting ? 'Giriş yapılıyor…' : 'Giriş yap'}
          </button>
        </form>
      </div>
    </main>
  )
}
