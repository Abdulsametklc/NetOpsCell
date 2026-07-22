import { useBadgeModalStore } from '../store/badgeModalStore'

/** CP5: rozet kazanma modal */
export function BadgeModal() {
  const open = useBadgeModalStore((s) => s.open)
  const badgeCode = useBadgeModalStore((s) => s.badgeCode)
  const badgeName = useBadgeModalStore((s) => s.badgeName)
  const close = useBadgeModalStore((s) => s.close)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-sm rounded-xl border border-amber-700/50 bg-slate-950 p-6 text-center shadow-xl"
      >
        <p className="text-xs uppercase tracking-wide text-amber-500">Rozet kazanıldı</p>
        <h2 className="mt-2 text-2xl font-semibold text-amber-200">{badgeName}</h2>
        <p className="mt-1 font-mono text-xs text-slate-500">{badgeCode}</p>
        <button
          type="button"
          onClick={close}
          className="mt-6 w-full rounded bg-amber-700 py-2.5 text-sm font-medium hover:bg-amber-600"
        >
          Harika
        </button>
      </div>
    </div>
  )
}
