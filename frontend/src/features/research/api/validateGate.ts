/*
 * Research zone — validation gate-state（後端 8.H.7 / S3）。
 * GET /research/validate/{id}/gate-state：當前 validation_status + stage + 轉移歷史。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface ValidationEvent {
  run_id: string
  validation_status: string
  stage: string
  note: string
  at: string
}

export interface GateState {
  run_id: string
  validation_status: string | null
  stage: string | null
  history: ValidationEvent[]
}

/** GET /research/validate/{run_id}/gate-state */
export function getGateState(runId: string): Promise<ApiResult<GateState>> {
  return http<GateState>(`/research/validate/${encodeURIComponent(runId)}/gate-state`)
}
