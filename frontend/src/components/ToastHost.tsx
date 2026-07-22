import { useToastStore } from '../store/toastStore'

const kindClass: Record<string, string> = {
  info: 'border-tc-navy-300 bg-white text-tc-navy-900 dark:border-tc-navy-600 dark:bg-tc-navy-900 dark:text-slate-100',
  success:
    'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950/90 dark:text-emerald-100',
  badge:
    'border-tc-yellow-400 bg-tc-yellow-50 text-tc-navy-900 dark:border-tc-yellow-600 dark:bg-tc-navy-900 dark:text-tc-yellow-100',
  warning:
    'border-orange-300 bg-orange-50 text-orange-900 dark:border-orange-700 dark:bg-orange-950/90 dark:text-orange-100',
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
          className={`rounded-lg border px-4 py-3 text-sm shadow-lg ${kindClass[t.kind] ?? kindClass.info}`}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-semibold">{t.title}</p>
              {t.message && <p className="mt-0.5 text-xs opacity-80">{t.message}</p>}
            </div>
            <button
              type="button"
              className="opacity-60 hover:opacity-100"
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
