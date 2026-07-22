/** Auth request/response — ARCHITECTURE.md §4.1; CONTRACTS §4.2 JWT */

export const Role = {
  MUSTERI: 'MUSTERI',
  SAHA_TEKNISYENI: 'SAHA_TEKNISYENI',
  NOC_OPERATORU: 'NOC_OPERATORU',
  SUPERVIZOR: 'SUPERVIZOR',
  ADMIN: 'ADMIN',
} as const
export type Role = (typeof Role)[keyof typeof Role]

export interface JWTPayload {
  sub: string
  role: Role | string
  specializations?: string[]
  regions?: string[]
  token_type?: string
  iat: number
  exp: number
}

export interface TokenPair {
  access_token: string
  refresh_token: string
}

export type PersonnelLoginRequest = {
  email: string
  password: string
}

export type CustomerLoginRequest = {
  gsm: string
  otp: string
}

export type LoginRequest = PersonnelLoginRequest | CustomerLoginRequest

export interface RefreshRequest {
  refresh_token: string
}

export interface UserProfile {
  id: string
  role: Role | string
  first_name?: string
  last_name?: string
  email?: string | null
  gsm?: string | null
  specializations?: string[]
  regions?: string[]
}
