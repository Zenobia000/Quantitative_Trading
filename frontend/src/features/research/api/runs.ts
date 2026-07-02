/*
 * Research zone — runs 端點（shipped：GET /runs, /runs/{id}, /runs/compare）。
 * 形狀取自 OpenAPI 生成型別（禁手寫）：
 * - GET /runs   → RunSummary[]（run_id, strategy, gate_status, hypothesis, metrics, is_start, is_end）
 * - GET /runs/{id} → RunRecord（run_id 保證 + 其餘 ledger 欄位 pass-through：strategy/params/engine/
 *   stocks/window/metrics/gate_status/gate_summary/created_at）
 */
import { http } from '@/services/http'
import type { components } from '@/types/api.gen'
import type { ApiResult } from '@/types/domain'

/** GET /runs 的一列（list 投影）。 */
export type RunRow = components['schemas']['RunSummary']
/** GET /runs/{id} 的完整 ledger record（run_id 保證，其餘欄位 pass-through）。 */
export type RunDetail = components['schemas']['RunRecord']

/** GET /runs — runs 主表（doc 25 裸根）。strategy_id/status filter 為前瞻參數（後端目前只分頁）。 */
export function listRuns(params?: {
  strategy_id?: string
  status?: string
  page?: number
  limit?: number
}): Promise<ApiResult<RunRow[]>> {
  return http<RunRow[]>('/runs', { query: params })
}

/** GET /runs/{run_id} — 單一 run 完整 record */
export function getRun(runId: string): Promise<ApiResult<RunDetail>> {
  return http<RunDetail>(`/runs/${encodeURIComponent(runId)}`)
}
