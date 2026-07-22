import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { logout } from '../api/authApi'
import { Role } from '../api/types'
import { homePathForRole } from '../lib/roleRoutes'
import { useAuthStore } from '../store/authStore'
import { LogoMark } from './LogoMark'
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
  const isHome = location.pathname === homePathForRole(role)

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  function onBack() {
    if (window.history.length > 1) navigate(-1)
    else navigate(homePathForRole(role))
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
      <header className="bg-tc-navy-600 text-white shadow-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8 sm:py-5">
          <div className="flex items-center gap-3">
            {!isHome && (
              <button
                type="button"
                onClick={onBack}
                aria-label="Geri git"
                className="flex h-9 w-9 items-center justify-center rounded-md text-white/80 transition hover:bg-white/10 hover:text-white"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}
            <Link to="/" className="flex items-center gap-2">
              <LogoMark className="h-9 w-9 sm:h-10 sm:w-10" />
              <span className="text-fluid-brand font-bold tracking-tight">
                NetOps<span className="text-tc-yellow-400">Cell</span>
              </span>
            </Link>
            <span className="hidden h-6 w-px bg-white/15 sm:block" />
            <div className="hidden sm:block">
              <p className="text-fluid-pagetitle font-bold text-white">{title}</p>
              {subtitle && <p className="text-xs font-medium text-white/60">{subtitle}</p>}
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-1 text-sm font-semibold sm:text-base">
            {items.map((item) => {
              const active = location.pathname === item.to
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`rounded-md px-3 py-2 transition ${
                    active ? 'bg-white/10 text-tc-yellow-400' : 'text-white/75 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  {item.label}
                </Link>
              )
            })}
            <span className="mx-1 hidden h-6 w-px bg-white/15 md:block" />
            <span className="hidden text-xs text-white/50 md:inline">
              {user?.first_name ?? 'Kullanıcı'} · {role}
            </span>
            <ThemeToggle />
            <button
              type="button"
              onClick={onLogout}
              className="rounded-md border border-white/20 px-3 py-2 text-xs font-medium text-white/85 transition hover:bg-white/10 sm:text-sm"
            >
              Çıkış
            </button>
          </nav>
        </div>
        <div className="h-0.5 w-full bg-gradient-to-r from-tc-yellow-500 via-tc-yellow-300 to-tc-yellow-500" />
      </header>
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-8">
        <div className="mb-4 sm:hidden">
          <p className="text-xl font-bold">{title}</p>
          {subtitle && <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
        {children}
      </div>
    </div>
  )
}
