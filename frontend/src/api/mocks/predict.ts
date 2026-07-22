import type { PredictResponse, ResponseEnvelope } from '../types'
import {
  FaultType,
  PredictionMethod,
  Priority,
  Suggestion,
} from '../types'

export const mockPredictSuccess: ResponseEnvelope<PredictResponse> = {
  success: true,
  data: {
    probability: 0.91,
    fault_type: FaultType.ISINMA,
    priority: Priority.KRITIK,
    suggestion: Suggestion.ACIL,
    method: PredictionMethod.RULE_FALLBACK,
    confidence_explanation:
      'Yüksek sıcaklık ve paket kaybı birlikte ISINMA arızasını işaret ediyor.',
  },
  error: null,
}

export const mockPredictValidationError: ResponseEnvelope<null> = {
  success: false,
  data: null,
  error: {
    code: 'VALIDATION_ERROR',
    message: 'packet_loss 0-100 aralığında olmalı',
    violations: null,
    retry_after_seconds: null,
  },
}
