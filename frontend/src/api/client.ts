import type { ResponseEnvelope } from './types'
import { useAuthStore } from '../store/authStore'

const baseUrl = () =>
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://localhost:8000'

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

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<ResponseEnvelope<T>> {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json')
  }

  const token = useAuthStore.getState().accessToken
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const url = `${baseUrl()}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, { ...init, headers })

  let envelope: ResponseEnvelope<T>
  try {
    envelope = (await res.json()) as ResponseEnvelope<T>
  } catch {
    throw new ApiError(`Invalid JSON from ${url}`, res.status)
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
  return baseUrl()
}
