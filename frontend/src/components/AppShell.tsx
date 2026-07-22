import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { logout } from '../api/authApi'
import { Role } from '../api/types'
import { useAuthStore } from '../store/authStore'
import { ThemeToggle } from './ThemeToggle'

interface AppShellProps {
  title: string
  subtitle?: string
  children: ReactNode
}

interface NavItem {
  to: string
  label: string
}

export function AppShell({ title, subtitle, children }: AppShellProps) {
  const user = useAuthStore((s) => s.user)
  const role = user?.role
  const navigate = useNavigate()
  const location = useLocation()

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const items: NavItem[] = []
  if (role === Role.SAHA_TEKNISYENI || role === Role.SUPERVIZOR || role === Role.ADMIN) {
    items.push({ to: '/teknisyen', label: 'Teknisyen' })
  }
  if (role === Role.NOC_OPERATORU || role === Role.SUPERVIZOR || role === Role.ADMIN) {
    items.push({ to: '/noc', label: 'NOC' })
  }
  if (role === Role.SUPERVIZOR || role === Role.ADMIN) {
    items.push({ to: '/dashboard', label: 'Dashboard' })
  }
  if (role === Role.ADMIN) {
    items.push({ to: '/admin', label: 'Admin' })
  }
  items.push({ to: '/liderlik', label: 'Liderlik' })
  items.push({ to: '/profil', label: 'Profil' })

  return (
    <div className="min-h-screen bg-slate-50 text-tc-navy-950 dark:bg-tc-navy-950 dark:text-slate-100">
      <header className="bg-tc-navy-900 text-white shadow-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-tc-yellow-500 text-sm font-black text-tc-navy-950">
                N
              </span>
              <span className="text-base font-bold tracking-tight">
                NetOps<span className="text-tc-yellow-400">Cell</span>
              </span>
            </Link>
            <span className="hidden h-5 w-px bg-white/15 sm:block" />
            <div className="hidden sm:block">
              <p className="text-sm font-medium text-white/90">{title}</p>
              {subtitle && <p className="text-[11px] text-white/50">{subtitle}</p>}
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-1 text-sm">
            {items.map((item) => {
              const active = location.pathname === item.to
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`rounded-md px-2.5 py-1.5 transition ${
                    active ? 'bg-white/10 text-tc-yellow-400' : 'text-white/75 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  {item.label}
                </Link>
              )
            })}
            <span className="mx-1 hidden h-5 w-px bg-white/15 md:block" />
            <span className="hidden text-xs text-white/50 md:inline">
              {user?.first_name ?? 'Kullanıcı'} · {role}
            </span>
            <ThemeToggle />
            <button
              type="button"
              onClick={onLogout}
              className="rounded-md border border-white/20 px-3 py-1.5 text-xs font-medium text-white/85 transition hover:bg-white/10"
            >
              Çıkış
            </button>
          </nav>
        </div>
        <div className="h-0.5 w-full bg-gradient-to-r from-tc-yellow-500 via-tc-yellow-300 to-tc-yellow-500" />
      </header>
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <div className="mb-4 sm:hidden">
          <p className="text-lg font-semibold">{title}</p>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
        {children}
      </div>
    </div>
  )
}
