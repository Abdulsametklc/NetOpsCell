import { getApiBaseUrl } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { mockPredictSuccess } from '../api/mocks/predict'

export function HomePage() {
  const authenticated = useAuthStore((s) => s.isAuthenticated())
  const mockFault = mockPredictSuccess.data?.fault_type

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">NetOpsCell</h1>
      <p className="text-slate-400 text-sm">
        Frontend CP1 scaffold — Gateway:{' '}
        <code className="text-sky-300">{getApiBaseUrl()}</code>
      </p>
      <p className="text-xs text-slate-500">
        Auth: {authenticated ? 'oturum açık' : 'oturum yok'} · Mock fault:{' '}
        {mockFault ?? '—'}
      </p>
    </main>
  )
}
