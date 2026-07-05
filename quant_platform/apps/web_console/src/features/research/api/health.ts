/*
 * Research zone — 13 指標健康表（後端 6.1.3 / v2.md §4.3.1）。
 * GET /research/validate/{id}/health：把某 run 儲存的 metrics 投影到 green/yellow/red 分帶。
 * 這是真投影（非 pending stub）—— 有 metrics 的 run 回真燈號；缺漏的指標回 na（絕不靜默判綠）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export type HealthLight = 'green' | 'yellow' | 'red' | 'na'

export interface HealthRow {
  key: string
  label: string
  value: number | null
  light: HealthLight
}

export interface HealthReport {
  rows: HealthRow[]
  counts: Record<HealthLight, number>
  all_green: boolean
}

/** GET /research/validate/{run_id}/health */
export function getValidateHealth(runId: string): Promise<ApiResult<HealthReport>> {
  return http<HealthReport>(`/research/validate/${encodeURIComponent(runId)}/health`)
}
