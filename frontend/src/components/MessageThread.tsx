import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { IncidentMessage } from '../api/types'
import { listMessages, postMessage } from '../api/messageApi'
import { ApiError } from '../api/client'
import { EmptyState, ErrorState, LoadingState } from './UiStates'

interface MessageThreadProps {
  incidentId: string
  incidentNumber: string
}

export function MessageThread({ incidentId, incidentNumber }: MessageThreadProps) {
  const [messages, setMessages] = useState<IncidentMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setMessages(await listMessages(incidentId))
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Mesajlar alınamadı')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [incidentId])

  async function onSend(e: FormEvent) {
    e.preventDefault()
    const content = text.trim()
    if (!content) return
    setSending(true)
    setError(null)
    try {
      const msg = await postMessage(incidentId, content)
      setMessages((prev) => [...prev, msg])
      setText('')
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Gönderilemedi')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/60 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h4 className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Mesajlaşma · {incidentNumber}
        </h4>
        <button
          type="button"
          className="text-xs text-sky-400 hover:underline"
          onClick={() => void load()}
        >
          Yenile
        </button>
      </div>

      {loading && <LoadingState message="Mesajlar yükleniyor…" />}
      {error && <ErrorState message={error} />}
      {!loading && !error && messages.length === 0 && (
        <EmptyState message="Henüz mesaj yok." />
      )}
      {!loading && messages.length > 0 && (
        <ul className="mb-3 max-h-48 space-y-2 overflow-y-auto text-sm">
          {messages.map((m) => (
            <li key={m.id} className="rounded border border-slate-800/80 bg-slate-900/50 px-3 py-2">
              <div className="mb-0.5 flex justify-between gap-2 text-xs text-slate-500">
                <span>
                  {m.sender_name ?? m.sender_role}
                </span>
                <span>{new Date(m.created_at).toLocaleTimeString('tr-TR')}</span>
              </div>
              <p className="text-slate-200">{m.content}</p>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={onSend} className="flex gap-2">
        <input
          className="flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Mesaj yaz…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={sending}
        />
        <button
          type="submit"
          disabled={sending || !text.trim()}
          className="rounded bg-sky-700 px-3 py-2 text-xs font-medium hover:bg-sky-600 disabled:opacity-60"
        >
          Gönder
        </button>
      </form>
    </div>
  )
}
