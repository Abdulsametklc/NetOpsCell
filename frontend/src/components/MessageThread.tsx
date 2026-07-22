import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { IncidentMessage } from '../api/types'
import { listMessages, postMessage } from '../api/messageApi'
import { ApiError } from '../api/client'
import { EmptyState, ErrorState, LoadingState } from './UiStates'
import { Button, Input } from './ui'

interface MessageThreadProps {
  incidentId: string
  incidentNumber: string
  /** false ise (rolünüz bu vakada mesajlaşma yetkisine sahip değilse) gönderim
   * formu devre dışı gösterilir - mesajlar yine de okunabilir. */
  canSend?: boolean
}

export function MessageThread({ incidentId, incidentNumber, canSend = true }: MessageThreadProps) {
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
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-tc-navy-800 dark:bg-tc-navy-950/60">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h4 className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Mesajlaşma · {incidentNumber}
        </h4>
        <button
          type="button"
          className="text-xs font-medium text-tc-navy-700 hover:underline dark:text-tc-yellow-400"
          onClick={() => void load()}
        >
          Yenile
        </button>
      </div>

      {loading && <LoadingState message="Mesajlar yükleniyor…" />}
      {error && <ErrorState message={error} />}
      {!loading && !error && messages.length === 0 && <EmptyState message="Henüz mesaj yok." />}
      {!loading && messages.length > 0 && (
        <ul className="mb-3 max-h-48 space-y-2 overflow-y-auto text-sm">
          {messages.map((m) => (
            <li
              key={m.id}
              className="rounded border border-slate-200 bg-white px-3 py-2 dark:border-tc-navy-800/80 dark:bg-tc-navy-900/50"
            >
              <div className="mb-0.5 flex justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span>{m.sender_name ?? m.sender_role}</span>
                <span>{new Date(m.created_at).toLocaleTimeString('tr-TR')}</span>
              </div>
              <p className="text-tc-navy-900 dark:text-slate-200">{m.content}</p>
            </li>
          ))}
        </ul>
      )}

      {canSend ? (
        <form onSubmit={onSend} className="flex gap-2">
          <Input
            className="flex-1"
            placeholder="Mesaj yaz…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={sending}
          />
          <Button type="submit" variant="primary" size="sm" disabled={sending || !text.trim()}>
            Gönder
          </Button>
        </form>
      ) : (
        <p className="rounded border border-dashed border-slate-300 px-3 py-2 text-xs text-slate-400 dark:border-tc-navy-800 dark:text-slate-500">
          Bu vakada mesaj yazma yetkiniz yok — sadece atanan teknisyen ve NOC operatörü yazabilir.
        </p>
      )}
    </div>
  )
}
