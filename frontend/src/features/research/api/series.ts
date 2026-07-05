/*
 * Research zone — run computed series（後端 8.H.3 / S4）。
 * GET /runs/{id}/equity · /runs/{id}/trades（端點已上線），讀 per-run sidecar；未持久化則
 * meta.data_source=pending（誠實空態，非後端缺件）。後端回泛型 Envelope 無 response_model，
 * 故 data 形狀以手寫 view-model 承載（型別技術債；後端補 response_model 後可改 api.gen）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface RunEquity {
  run_id: string
  equity: number[]
  drawdown: number[]
}

export interface RunTrade {
  ret: number
  hold: number
  entry_structure: number
  [k: string]: unknown
}

export interface RunTrades {
  run_id: string
  trades: RunTrade[]
}

/** GET /runs/{id}/equity — 權益曲線 + 回撤 */
export function getRunEquity(runId: string): Promise<ApiResult<RunEquity>> {
  return http<RunEquity>(`/runs/${encodeURIComponent(runId)}/equity`)
}

/** GET /runs/{id}/trades — 逐筆交易 */
export function getRunTrades(runId: string): Promise<ApiResult<RunTrades>> {
  return http<RunTrades>(`/runs/${encodeURIComponent(runId)}/trades`)
}
