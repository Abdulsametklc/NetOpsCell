import type { LoginRequest, TokenPair, UserProfile } from './types'
import { Role } from './types'
import { apiFetch, getApiBaseUrl } from './client'
import { mockProfile, mockTokenPair } from './mocks/auth'
import { useAuthStore } from '../store/authStore'

function useAuthMock(): boolean {
  return import.meta.env.VITE_USE_AUTH_MOCK === 'true'
}

function isPersonnelLogin(
  body: LoginRequest,
): body is { email: string; password: string } {
  return 'email' in body
}

function inferMockRole(email: string): Role {
  const e = email.toLowerCase()
  if (e.includes('admin')) return Role.ADMIN
  if (e.includes('noc')) return Role.NOC_OPERATORU
  if (e.includes('super')) return Role.SUPERVIZOR
  return Role.SAHA_TEKNISYENI
}

export async function login(body: LoginRequest): Promise<TokenPair> {
  if (useAuthMock()) {
    const role = isPersonnelLogin(body)
      ? inferMockRole(body.email)
      : Role.MUSTERI
    const pair = mockTokenPair(role)
    useAuthStore.getState().setTokens(pair.access_token, pair.refresh_token)
    useAuthStore.getState().setUser(mockProfile(role))
    return pair
  }

  const envelope = await apiFetch<TokenPair>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
    skipAuth: true,
  })
  if (!envelope.data) throw new Error('Login cevabında token yok')
  useAuthStore.getState().setTokens(envelope.data.access_token, envelope.data.refresh_token)
  return envelope.data
}

export async function fetchMe(): Promise<UserProfile | null> {
  if (useAuthMock()) {
    const role = useAuthStore.getState().role() ?? Role.SAHA_TEKNISYENI
    const profile = mockProfile(role)
    useAuthStore.getState().setUser(profile)
    return profile
  }

  const envelope = await apiFetch<UserProfile>('/api/v1/auth/me')
  if (envelope.data) useAuthStore.getState().setUser(envelope.data)
  return envelope.data
}

export async function logout(): Promise<void> {
  const { refreshToken, clear } = useAuthStore.getState()
  try {
    if (!useAuthMock() && refreshToken) {
      await apiFetch<null>('/api/v1/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
        skipRefresh: true,
      })
    }
  } catch {
    /* clear local session anyway */
  } finally {
    clear()
  }
}

export function authModeLabel(): string {
  return useAuthMock()
    ? `mock auth (${getApiBaseUrl()})`
    : `live API (${getApiBaseUrl()})`
}
