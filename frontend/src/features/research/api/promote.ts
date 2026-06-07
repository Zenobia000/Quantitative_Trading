/*
 * Research zone — promotion state machine（後端 8.H.7 / S3）。
 * GET /research/promote/{id}（current stage + gates + history）、POST（前進一階）、
 * GET /research/promote/{id}/audit（immutable audit trail）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface PromotionGate {
  stage: string
  reached: boolean
}

export interface PromotionState {
  strategy_id: string
  stage: string
  gates: PromotionGate[]
  history: PromotionEvent[]
}

export interface PromotionEvent {
  strategy_id: string
  stage: string
  note: string
  actor: string
  at: string
}

/** GET /research/promote/{strategy_id} */
export function getPromoteState(strategyId: string): Promise<ApiResult<PromotionState>> {
  return http<PromotionState>(`/research/promote/${encodeURIComponent(strategyId)}`)
}

/** POST /research/promote/{strategy_id} — 前進一階（draft→paper→live） */
export function advancePromote(
  strategyId: string,
  body: { to_stage: string; note?: string; actor?: string },
): Promise<ApiResult<{ strategy_id: string; stage: string }>> {
  return http(`/research/promote/${encodeURIComponent(strategyId)}`, { method: 'POST', json: body })
}

/** GET /research/promote/{strategy_id}/audit */
export function getPromoteAudit(strategyId: string): Promise<ApiResult<PromotionEvent[]>> {
  return http<PromotionEvent[]>(`/research/promote/${encodeURIComponent(strategyId)}/audit`)
}
