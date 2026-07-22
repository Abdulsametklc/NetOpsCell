interface StateProps {
  message: string
}

export function LoadingState({ message = 'Yükleniyor…' }: { message?: string }) {
  return (
    <p className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-tc-yellow-500 border-t-transparent" />
      {message}
    </p>
  )
}

export function ErrorState({ message }: StateProps) {
  return (
    <p
      className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300"
      role="alert"
    >
      {message}
    </p>
  )
}

export function EmptyState({ message }: StateProps) {
  return <p className="text-sm text-slate-500 dark:text-slate-400">{message}</p>
}
