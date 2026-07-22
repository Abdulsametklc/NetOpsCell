import { useToastStore } from '../store/toastStore'

const kindClass: Record<string, string> = {
  info: 'border-sky-700 bg-sky-950/90',
  success: 'border-emerald-700 bg-emerald-950/90',
  badge: 'border-amber-600 bg-amber-950/90',
  warning: 'border-orange-700 bg-orange-950/90',
}

/** CP4 realtime toast iskeleti — CP5'te Notification Hub WS bağlanır */
export function ToastHost() {
  const toasts = useToastStore((s) => s.toasts)
  const dismiss = useToastStore((s) => s.dismiss)

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`rounded-lg border px-4 py-3 text-sm text-slate-100 shadow-lg ${kindClass[t.kind] ?? kindClass.info}`}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-medium">{t.title}</p>
              {t.message && <p className="mt-0.5 text-xs text-slate-300">{t.message}</p>}
            </div>
            <button
              type="button"
              className="text-slate-400 hover:text-white"
              onClick={() => dismiss(t.id)}
              aria-label="Kapat"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
