import type { Role, TokenPair, UserProfile } from '../types'

function b64url(obj: unknown): string {
  const json = JSON.stringify(obj)
  const b64 = btoa(json)
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** Dev-only mock access JWT (unsigned) so role routing works offline. */
export function mockAccessToken(role: Role | string, sub = 'mock-user-1'): string {
  const header = b64url({ alg: 'RS256', typ: 'JWT' })
  const now = Math.floor(Date.now() / 1000)
  const payload = b64url({
    sub,
    role,
    specializations: ['DONANIM', 'ISINMA'],
    regions: ['IST-AVRUPA'],
    token_type: 'access',
    iat: now,
    exp: now + 15 * 60,
  })
  return `${header}.${payload}.mock`
}

export function mockTokenPair(role: Role | string): TokenPair {
  return {
    access_token: mockAccessToken(role),
    refresh_token: `mock-refresh-${role}-${Date.now()}`,
  }
}

export function mockProfile(role: Role | string): UserProfile {
  return {
    id: 'mock-user-1',
    role,
    first_name: 'Demo',
    last_name: 'Teknisyen',
    email: role === 'MUSTERI' ? null : 'teknisyen@netopscell.demo',
    gsm: role === 'MUSTERI' ? '5551234567' : null,
    specializations: ['DONANIM', 'ISINMA'],
    regions: ['IST-AVRUPA'],
  }
}
