/*
 * Research zone — WFA folds（後端 6.2.2 / S7）。
 * GET /research/validate/{id}/wfa：v2.md §4.4.1 fold 日期窗（IS252/OOS63 rolling）。
 * folds 為 data-free 真實窗；scatter（per-fold IS/OOS 績效）需 parquet → meta.scatter=pending。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface WfaFold {
  fold: number
  is_start: string
  is_end: string
  oos_start: string
  oos_end: string
}

export interface WfaScatterPoint {
  fold: number
  is_perf: number
  oos_perf: number
}

export interface WfaResult {
  folds: WfaFold[]
  scatter: WfaScatterPoint[]
  criteria: Record<string, string>
}

/** GET /research/validate/{run_id}/wfa */
export function getValidateWfa(runId: string): Promise<ApiResult<WfaResult>> {
  return http<WfaResult>(`/research/validate/${encodeURIComponent(runId)}/wfa`)
}
