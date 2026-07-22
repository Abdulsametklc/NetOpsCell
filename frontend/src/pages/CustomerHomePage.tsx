import { AppShell } from '../components/AppShell'
import { Card } from '../components/ui'
import { useAuthStore } from '../store/authStore'

/** CP2 stub — müşteri ekranları sonraki checkpoint'lerde */
export function CustomerHomePage() {
  const user = useAuthStore((s) => s.user)

  return (
    <AppShell title="NetOpsCell — Müşteri" subtitle="Şebeke durumu">
      <Card className="flex flex-col items-center gap-2 p-10 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-tc-yellow-100 text-2xl dark:bg-tc-yellow-500/15">
          📶
        </span>
        <h1 className="text-xl font-semibold">Hoş geldiniz</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Müşteri oturumu ({user?.gsm ?? user?.id}) — kişisel arıza takip paneli yakında.
        </p>
      </Card>
    </AppShell>
  )
}
