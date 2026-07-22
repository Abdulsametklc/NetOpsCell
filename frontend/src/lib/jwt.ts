import type { JWTPayload } from '../api/types'

function b64UrlToJson<T>(segment: string): T {
  const padded = segment.replace(/-/g, '+').replace(/_/g, '/')
  const pad = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4))
  const json = atob(padded + pad)
  return JSON.parse(json) as T
}

export function decodeJwtPayload(token: string): JWTPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    return b64UrlToJson<JWTPayload>(parts[1])
  } catch {
    return null
  }
}

export function isJwtExpired(token: string, skewSeconds = 30): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return true
  return payload.exp * 1000 <= Date.now() + skewSeconds * 1000
}
