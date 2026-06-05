/*
 * Research zone — runs 端點（shipped：GET /runs, /runs/{id}, /runs/compare）。
 * 注意：v0.6 後端 Envelope.data 為 generic（未逐端點 typing），故 data 形狀暫以本檔 view-model 承載；
 * 待後端依 doc 25 補 response_model，改用 src/types/api.gen.ts 生成型別（GOAL.md §6 companion goal）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

/** runs ledger 列（view-model；後端 typed 後以 api.gen 取代） */
export interface RunRow {
  run_id: string
  strategy_id?: string
  status?: string
  created_at?: string
  // metrics 動態欄位
  [k: string]: unknown
}

/** GET /runs — runs 主表（doc 25 裸根） */
export function listRuns(params?: {
  strategy_id?: string
  status?: string
  page?: number
  limit?: number
}): Promise<ApiResult<RunRow[]>> {
  return http<RunRow[]>('/runs', { query: params })
}

/** GET /runs/{run_id} — 單一 run */
export function getRun(runId: string): Promise<ApiResult<RunRow>> {
  return http<RunRow>(`/runs/${encodeURIComponent(runId)}`)
}
