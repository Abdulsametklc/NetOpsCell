/** Mirrors docs/CONTRACTS.md §4.2 */

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
