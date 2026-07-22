import type { ResponseEnvelope, TokenPair } from './types'
import { mockTokenPair } from './mocks/auth'
import { useAuthStore } from '../store/authStore'

function resolveBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined
  return (raw ?? 'http://localhost:8000').replace(/\/$/, '')
}

function useAuthMock(): boolean {
  return import.meta.env.VITE_USE_AUTH_MOCK === 'true'
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

  if (!skipAuth) {
    const token = useAuthStore.getState().accessToken
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  const url = `${resolveBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, { ...rest, headers })

  let envelope: ResponseEnvelope<T>
  try {
    envelope = (await res.json()) as ResponseEnvelope<T>
  } catch {
    throw new ApiError(`Invalid JSON from ${url}`, res.status)
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
  return resolveBaseUrl()
}
