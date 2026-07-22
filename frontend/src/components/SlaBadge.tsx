import { useEffect, useState } from 'react'

export type SlaTone = 'ok' | 'warn' | 'urgent' | 'breached' | 'idle'

export function computeSla(iso: string | null | undefined, slaStatus?: string | null): {
  tone: SlaTone
  label: string
  remainingMs: number | null
} {
  if (slaStatus === 'BREACHED') {
    return { tone: 'breached', label: 'SLA aşıldı', remainingMs: null }
  }
  if (slaStatus === 'MET' || !iso) {
    return { tone: 'idle', label: slaStatus === 'MET' ? 'SLA karşılandı' : 'SLA yok', remainingMs: null }
  }

  const remainingMs = new Date(iso).getTime() - Date.now()
  if (remainingMs < 0) {
    return { tone: 'breached', label: 'SLA aşıldı', remainingMs }
  }

  const min = Math.round(remainingMs / 60000)
  const label =
    min < 60 ? `${min} dk kaldı` : `${Math.floor(min / 60)} sa ${min % 60} dk`

  // <15 dk kırmızı/urgent, <60 dk turuncu/warn, aksi yeşil/ok
  if (min < 15) return { tone: 'urgent', label, remainingMs }
  if (min < 60) return { tone: 'warn', label, remainingMs }
  return { tone: 'ok', label, remainingMs }
}

const toneClass: Record<SlaTone, string> = {
  ok: 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800',
  warn: 'bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-700',
  urgent: 'bg-orange-50 text-orange-700 border-orange-300 dark:bg-orange-950/60 dark:text-orange-300 dark:border-orange-700',
  breached: 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-700',
  idle: 'bg-slate-100 text-slate-500 border-slate-300 dark:bg-tc-navy-900 dark:text-slate-500 dark:border-tc-navy-800',
}

interface SlaBadgeProps {
  slaDueAt?: string | null
  slaStatus?: string | null
  className?: string
}

/** CP5: renk kodlu SLA göstergesi (kırmızı / turuncu / uyarı / yeşil) */
export function SlaBadge({ slaDueAt, slaStatus, className = '' }: SlaBadgeProps) {
  const [, setTick] = useState(0)

  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 30_000)
    return () => window.clearInterval(id)
  }, [])

  const { tone, label } = computeSla(slaDueAt, slaStatus)

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${toneClass[tone]} ${className}`}
      title={slaDueAt ? new Date(slaDueAt).toLocaleString('tr-TR') : undefined}
    >
      SLA · {label}
    </span>
  )
}
