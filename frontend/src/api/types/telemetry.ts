/** Mirrors docs/CONTRACTS.md §2.1–2.2 */

import type {
  FaultType,
  PowerStatus,
  PredictionMethod,
  Priority,
  Suggestion,
} from './enums'

export interface TelemetryInput {
  station_code: string
  lat: number
  lng: number
  signal_strength: number
  packet_loss: number
  temperature: number
  power_status: PowerStatus
  recent_fault_count?: number
}

/** PredictRequest === TelemetryInput */
export type PredictRequest = TelemetryInput

export interface PredictResponse {
  probability: number
  fault_type: FaultType
  priority: Priority
  suggestion: Suggestion
  method: PredictionMethod
  confidence_explanation: string
}
