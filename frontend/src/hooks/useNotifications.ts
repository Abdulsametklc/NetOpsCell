import { useEffect, useRef } from 'react'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'
import { useBadgeModalStore } from '../store/badgeModalStore'

type HubEvent =
  | { event_type: 'badge.earned'; user_id: string; badge_code: string; earned_at?: string }
  | {
      event_type: 'incident.assigned'
      incident_id: string
      team_id?: string
      team_name?: string
    }
  | {
      event_type: 'incident.sla_breached'
      incident_id: string
      priority?: string
    }
  | {
      event_type: 'game.points_awarded'
      user_id: string
      points: number
      reason?: string
      new_total?: number
    }

function resolveWsUrl(token: string): string {
  const envUrl = import.meta.env.VITE_WS_URL as string | undefined
  if (envUrl) {
    const base = envUrl.replace(/\/$/, '')
    return `${base}?token=${encodeURIComponent(token)}`
  }
  const api = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'
  const u = new URL(api)
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
  u.pathname = '/api/v1/ws/notifications'
  u.search = `token=${encodeURIComponent(token)}`
  return u.toString()
}

function handleEvent(ev: HubEvent) {
  const push = useToastStore.getState().push
  const me = useAuthStore.getState().user?.id

  switch (ev.event_type) {
    case 'badge.earned':
      if (me && ev.user_id !== me) return
      push('badge', 'Yeni rozet!', ev.badge_code)
      useBadgeModalStore.getState().show(ev.badge_code)
      break
    case 'incident.assigned':
      push(
        'info',
        'Yeni atama',
        ev.team_name
          ? `${ev.team_name} · ${ev.incident_id.slice(0, 8)}…`
          : `Vaka ${ev.incident_id.slice(0, 8)}…`,
      )
      break
    case 'incident.sla_breached':
      push('warning', 'SLA aşıldı', `Vaka ${ev.incident_id.slice(0, 8)}… · ${ev.priority ?? ''}`)
      break
    case 'game.points_awarded':
      if (me && ev.user_id !== me) return
      push('success', `+${ev.points} puan`, ev.reason ?? `Toplam ${ev.new_total ?? ''}`)
      break
    default:
      break
  }
}

/**
 * Notification Hub istemcisi.
 * VITE_USE_WS_MOCK=true iken periyodik demo event üretir (Hub yokken).
 * false iken Gateway WS'e bağlanır.
 */
export function useNotifications() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!accessToken) return

    const useMock = import.meta.env.VITE_USE_WS_MOCK === 'true'

    if (useMock) {
      const t1 = window.setTimeout(() => {
        handleEvent({
          event_type: 'incident.assigned',
          incident_id: '11111111-1111-1111-1111-111111111111',
          team_name: 'IST-AVRUPA-A',
        })
      }, 4000)
      const t2 = window.setTimeout(() => {
        handleEvent({
          event_type: 'badge.earned',
          user_id: useAuthStore.getState().user?.id ?? 'mock-user-1',
          badge_code: 'ILK_MUDAHALE',
        })
      }, 12000)
      return () => {
        window.clearTimeout(t1)
        window.clearTimeout(t2)
      }
    }

    const url = resolveWsUrl(accessToken)
    let closed = false
    let retry: number | undefined

    function connect() {
      if (closed) return
      const ws = new WebSocket(url)
      wsRef.current = ws
      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(String(msg.data)) as HubEvent
          handleEvent(data)
        } catch {
          /* ignore malformed */
        }
      }
      ws.onclose = () => {
        wsRef.current = null
        if (!closed) retry = window.setTimeout(connect, 5000)
      }
      ws.onerror = () => {
        ws.close()
      }
    }

    connect()
    return () => {
      closed = true
      if (retry) window.clearTimeout(retry)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [accessToken])
}
