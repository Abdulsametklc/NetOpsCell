import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { fetchMe, login } from '../api/authApi'
import { useAuthStore } from '../store/authStore'
import { homePathForRole } from '../lib/roleRoutes'
import { ThemeToggle } from '../components/ThemeToggle'
import { LogoMark } from '../components/LogoMark'
import { Teknocan } from '../components/Teknocan'
import { Button, Field, Input, Pill } from '../components/ui'

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
            sec ? `Hesap kilitli. ${sec} sn sonra tekrar deneyin.` : 'Hesap kilitli. Daha sonra tekrar deneyin.',
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
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-br from-tc-navy-900 via-tc-navy-600 to-tc-navy-950 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(255,200,0,0.12),transparent_45%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_85%_100%,rgba(255,200,0,0.08),transparent_45%)]" />

      <div className="relative flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2">
          <LogoMark />
          <span className="text-lg font-bold tracking-tight">
            NetOps<span className="text-tc-yellow-400">Cell</span>
          </span>
        </div>
        <ThemeToggle />
      </div>

      <div className="relative flex min-h-[calc(100vh-88px)] items-start justify-center p-6 pt-16 sm:pt-24">
        <div className="w-full max-w-md">
          <div className="mb-6 text-center">
            <h1 className="text-3xl font-extrabold tracking-tight">Şebeke Operasyon Platformu</h1>
            <p className="mt-2 text-sm font-medium text-white/60">Devam etmek için giriş yapın</p>
          </div>

          <div className="mb-4 flex gap-2 rounded-full bg-white/5 p-1">
            <Pill
              active={tab === 'personnel'}
              className="flex-1"
              type="button"
              onClick={() => setTab('personnel')}
            >
              Personel
            </Pill>
            <Pill
              active={tab === 'customer'}
              className="flex-1"
              type="button"
              onClick={() => setTab('customer')}
            >
              Müşteri (GSM+OTP)
            </Pill>
          </div>

          <form
            onSubmit={onSubmit}
            className="space-y-4 rounded-2xl border border-white/10 bg-white/[0.06] p-6 shadow-2xl backdrop-blur-sm"
          >
            {tab === 'personnel' ? (
              <>
                <Field label="E-posta">
                  <Input
                    type="email"
                    autoComplete="username"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </Field>
                <Field label="Şifre">
                  <Input
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required={!import.meta.env.VITE_USE_AUTH_MOCK}
                  />
                </Field>
              </>
            ) : (
              <>
                <Field label="GSM">
                  <Input inputMode="tel" value={gsm} onChange={(e) => setGsm(e.target.value)} required />
                </Field>
                <Field label="OTP">
                  <Input value={otp} onChange={(e) => setOtp(e.target.value)} required />
                </Field>
              </>
            )}

            {error && (
              <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300" role="alert">
                {error}
              </p>
            )}
            {lockedHint && (
              <p
                className="rounded-lg border border-tc-yellow-500/30 bg-tc-yellow-500/10 px-3 py-2 text-sm text-tc-yellow-300"
                role="status"
              >
                {lockedHint}
              </p>
            )}

            <Button type="submit" variant="primary" disabled={submitting} className="w-full">
              {submitting ? 'Giriş yapılıyor…' : 'Giriş yap'}
            </Button>
          </form>
        </div>
      </div>

      <Teknocan />
    </main>
  )
}
