/** Mirrors docs/CONTRACTS.md §4.1 / §4.3 */

export const ErrorCode = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  WEAK_PASSWORD: 'WEAK_PASSWORD',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  ACCOUNT_LOCKED: 'ACCOUNT_LOCKED',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  TOKEN_INVALID: 'TOKEN_INVALID',
  TOKEN_REUSE_DETECTED: 'TOKEN_REUSE_DETECTED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  INVALID_TRANSITION: 'INVALID_TRANSITION',
  RATE_LIMITED: 'RATE_LIMITED',
  AI_SERVICE_UNAVAILABLE: 'AI_SERVICE_UNAVAILABLE',
} as const
export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode]

export interface ErrorDetail {
  code: string
  message: string
  violations?: string[] | null
  retry_after_seconds?: number | null
}

export interface ResponseEnvelope<T> {
  success: boolean
  data: T | null
  error: ErrorDetail | null
}
