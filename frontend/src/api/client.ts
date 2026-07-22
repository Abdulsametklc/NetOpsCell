import type { ResponseEnvelope, TokenPair } from './types'
import { mockTokenPair } from './mocks/auth'
import { useAuthStore } from '../store/authStore'

/** Boş = Vite dev proxy (aynı origin). Gateway gelince http://localhost:8000 */
function resolveBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined
  if (raw === undefined || raw === '') return ''
  return raw.replace(/\/$/, '')
}

function useAuthMock(): boolean {
  return import.meta.env.VITE_USE_AUTH_MOCK === 'true'
}

/** Gateway yokken Incident status için X-User-* (auth mock iken). Gateway gelince o enjekte eder. */
function shouldInjectUserHeaders(): boolean {
  return (
    useAuthMock() || import.meta.env.VITE_INJECT_USER_HEADERS === 'true'
  )
}

export class ApiError extends Error {
  status: number
  envelope?: ResponseEnvelope<unknown>

  constructor(
    message: string,
    status: number,
    envelope?: ResponseEnvelope<unknown>,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.envelope = envelope
  }
}

export type ApiFetchInit = RequestInit & {
  skipAuth?: boolean
  skipRefresh?: boolean
}

let refreshInFlight: Promise<boolean> | null = null

async function performRefresh(refreshToken: string): Promise<TokenPair> {
  if (useAuthMock()) {
    const role = useAuthStore.getState().role() ?? 'SAHA_TEKNISYENI'
    return mockTokenPair(role)
  }

  const url = `${resolveBaseUrl()}/api/v1/auth/refresh`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  const envelope = (await res.json()) as ResponseEnvelope<TokenPair>
  if (!res.ok || !envelope.success || !envelope.data) {
    throw new ApiError(
      envelope.error?.message ?? 'Refresh failed',
      res.status,
      envelope,
    )
  }
  return envelope.data
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = useAuthStore.getState().refreshToken
  if (!refreshToken) return false
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const pair = await performRefresh(refreshToken)
        useAuthStore.getState().setTokens(pair.access_token, pair.refresh_token)
        return true
      } catch {
        useAuthStore.getState().clear()
        return false
      } finally {
        refreshInFlight = null
      }
    })()
  }
  return refreshInFlight
}

export async function apiFetch<T>(
  path: string,
  init: ApiFetchInit = {},
): Promise<ResponseEnvelope<T>> {
  const { skipAuth, skipRefresh, ...rest } = init
  const headers = new Headers(rest.headers)
  if (!headers.has('Content-Type') && rest.body) {
    headers.set('Content-Type', 'application/json')
  }

  const { accessToken, user } = useAuthStore.getState()

  if (!skipAuth && accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  if (shouldInjectUserHeaders() && user?.id && user?.role) {
    if (!headers.has('X-User-Id')) headers.set('X-User-Id', user.id)
    if (!headers.has('X-User-Role')) headers.set('X-User-Role', String(user.role))
  }

  const url = `${resolveBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, { ...rest, headers })

  let envelope: ResponseEnvelope<T>
  try {
    envelope = (await res.json()) as ResponseEnvelope<T>
  } catch {
    throw new ApiError(`Invalid JSON from ${url || path}`, res.status)
  }

  const expired =
    res.status === 401 &&
    (envelope.error?.code === 'TOKEN_EXPIRED' ||
      envelope.error?.code === 'TOKEN_INVALID')

  if (expired && !skipRefresh && !skipAuth) {
    const ok = await tryRefresh()
    if (ok) {
      return apiFetch<T>(path, { ...init, skipRefresh: true })
    }
  }

  if (!res.ok || envelope.success === false) {
    throw new ApiError(
      envelope.error?.message ?? `Request failed (${res.status})`,
      res.status,
      envelope,
    )
  }

  return envelope
}

export function getApiBaseUrl(): string {
  const base = resolveBaseUrl()
  return base || '(vite-proxy → services)'
}
