/*
 * Research zone — compare（shipped：GET /runs/compare?baseline=）。
 * 後端以 baseline 為基準比較 runs ledger；回應 data 為 generic（view-model 暫承載）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface CompareRow {
  run_id?: string
  [k: string]: unknown
}

/** GET /runs/compare — 以 baseline 為基準的跨 run 比較 */
export function getCompare(baseline?: string): Promise<ApiResult<CompareRow[] | Record<string, unknown>>> {
  return http<CompareRow[] | Record<string, unknown>>('/runs/compare', { query: { baseline } })
}
