import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { logout } from '../api/authApi'
import { Role } from '../api/types'
import { useAuthStore } from '../store/authStore'

interface AppShellProps {
  title: string
  subtitle?: string
  children: ReactNode
}

export function AppShell({ title, subtitle, children }: AppShellProps) {
  const user = useAuthStore((s) => s.user)
  const role = user?.role
  const navigate = useNavigate()

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const showTech = role === Role.SAHA_TEKNISYENI || role === Role.SUPERVIZOR || role === Role.ADMIN
  const showNoc =
    role === Role.NOC_OPERATORU || role === Role.SUPERVIZOR || role === Role.ADMIN
  const showDash = role === Role.SUPERVIZOR || role === Role.ADMIN
  const showAdmin = role === Role.ADMIN

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-4 py-4 sm:px-6">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-lg font-semibold tracking-tight">{title}</p>
            {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
          </div>
          <nav className="flex flex-wrap items-center gap-1 text-sm sm:gap-2">
            {showTech && (
              <Link className="rounded px-2 py-1 text-slate-300 hover:bg-slate-900" to="/teknisyen">
                Teknisyen
              </Link>
            )}
            {showNoc && (
              <Link className="rounded px-2 py-1 text-slate-300 hover:bg-slate-900" to="/noc">
                NOC
              </Link>
            )}
            {showDash && (
              <Link className="rounded px-2 py-1 text-slate-300 hover:bg-slate-900" to="/dashboard">
                Dashboard
              </Link>
            )}
            {showAdmin && (
              <Link className="rounded px-2 py-1 text-slate-300 hover:bg-slate-900" to="/admin">
                Admin
              </Link>
            )}
            <Link className="rounded px-2 py-1 text-slate-300 hover:bg-slate-900" to="/liderlik">
              Liderlik
            </Link>
            <Link className="rounded px-2 py-1 text-slate-300 hover:bg-slate-900" to="/profil">
              Profil
            </Link>
            <span className="hidden text-slate-500 md:inline">
              {user?.first_name ?? 'Kullanıcı'} · {role}
            </span>
            <button
              type="button"
              onClick={onLogout}
              className="rounded border border-slate-700 px-3 py-1.5 hover:bg-slate-900"
            >
              Çıkış
            </button>
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">{children}</div>
    </main>
  )
}
