import { useBadgeModalStore } from '../store/badgeModalStore'
import { Button } from './ui'

/** CP5: rozet kazanma modal */
export function BadgeModal() {
  const open = useBadgeModalStore((s) => s.open)
  const badgeCode = useBadgeModalStore((s) => s.badgeCode)
  const badgeName = useBadgeModalStore((s) => s.badgeName)
  const close = useBadgeModalStore((s) => s.close)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-tc-navy-950/70 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-sm rounded-2xl border border-tc-yellow-500/40 bg-white p-6 text-center shadow-2xl dark:bg-tc-navy-900"
      >
        <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-tc-yellow-100 text-2xl dark:bg-tc-yellow-500/15">
          🏆
        </div>
        <p className="text-xs font-semibold uppercase tracking-wide text-tc-yellow-600 dark:text-tc-yellow-400">
          Rozet kazanıldı
        </p>
        <h2 className="mt-2 text-2xl font-bold text-tc-navy-950 dark:text-white">{badgeName}</h2>
        <p className="mt-1 font-mono text-xs text-slate-500 dark:text-slate-400">{badgeCode}</p>
        <Button variant="primary" onClick={close} className="mt-6 w-full">
          Harika
        </Button>
      </div>
    </div>
  )
}
