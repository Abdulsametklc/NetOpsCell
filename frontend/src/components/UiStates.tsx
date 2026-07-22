interface StateProps {
  message: string
}

export function LoadingState({ message = 'Yükleniyor…' }: { message?: string }) {
  return <p className="text-sm text-slate-500">{message}</p>
}

export function ErrorState({ message }: StateProps) {
  return (
    <p className="rounded border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-sm text-rose-300" role="alert">
      {message}
    </p>
  )
}

export function EmptyState({ message }: StateProps) {
  return <p className="text-sm text-slate-500">{message}</p>
}
