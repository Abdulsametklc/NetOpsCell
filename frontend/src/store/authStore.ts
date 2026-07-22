import { create } from 'zustand'
import type { Role, UserProfile } from '../api/types'
import { decodeJwtPayload } from '../lib/jwt'

const ACCESS_KEY = 'noc_access_token'
const REFRESH_KEY = 'noc_refresh_token'

function readStored(): { accessToken: string | null; refreshToken: string | null } {
  try {
    return {
      accessToken: localStorage.getItem(ACCESS_KEY),
      refreshToken: localStorage.getItem(REFRESH_KEY),
    }
  } catch {
    return { accessToken: null, refreshToken: null }
  }
}

function persist(accessToken: string | null, refreshToken: string | null) {
  try {
    if (accessToken) localStorage.setItem(ACCESS_KEY, accessToken)
    else localStorage.removeItem(ACCESS_KEY)
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken)
    else localStorage.removeItem(REFRESH_KEY)
  } catch {
    /* ignore quota / private mode */
  }
}

function profileFromAccess(accessToken: string | null): UserProfile | null {
  if (!accessToken) return null
  const payload = decodeJwtPayload(accessToken)
  if (!payload) return null
  return {
    id: payload.sub,
    role: payload.role,
    specializations: payload.specializations ?? [],
    regions: payload.regions ?? [],
  }
}

const initial = readStored()

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserProfile | null
  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: UserProfile | null) => void
  clear: () => void
  isAuthenticated: () => boolean
  role: () => Role | string | null
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: initial.accessToken,
  refreshToken: initial.refreshToken,
  user: profileFromAccess(initial.accessToken),
  setTokens: (accessToken, refreshToken) => {
    persist(accessToken, refreshToken)
    set({
      accessToken,
      refreshToken,
      user: profileFromAccess(accessToken),
    })
  },
  setUser: (user) => set({ user }),
  clear: () => {
    persist(null, null)
    set({ accessToken: null, refreshToken: null, user: null })
  },
  isAuthenticated: () => Boolean(get().accessToken),
  role: () => get().user?.role ?? null,
}))
