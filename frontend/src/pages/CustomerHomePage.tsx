import { useNavigate } from 'react-router-dom'
import { logout } from '../api/authApi'
import { useAuthStore } from '../store/authStore'

/** CP2 stub — müşteri ekranları sonraki checkpoint'lerde */
export function CustomerHomePage() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">NetOpsCell</h1>
      <p className="text-slate-400 text-sm">
        Müşteri oturumu ({user?.gsm ?? user?.id}) — panel CP3+
      </p>
      <button
        type="button"
        onClick={onLogout}
        className="rounded border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900"
      >
        Çıkış
      </button>
    </main>
  )
}
