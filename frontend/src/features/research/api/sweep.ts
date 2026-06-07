/*
 * Research zone — async sweep jobs（後端 8.H.6 / S2）。
 * POST /research/sweep（提交 grid-expansion 為背景 job，202 + job_id）、
 * GET /research/sweep/{job_id}/status（輪詢 queued→running→done|failed）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface SweepSubmit {
  job_id: string
  status: string
}

export interface SweepPlan {
  n_configs: number
  combos: Record<string, unknown>[]
}

export interface SweepJob {
  job_id: string
  kind: string
  status: string | null
  progress: number | null
  result?: SweepPlan | null
  error?: string | null
}

/** POST /research/sweep — 提交 grid */
export function submitSweep(grid: Record<string, unknown[]>): Promise<ApiResult<SweepSubmit>> {
  return http<SweepSubmit>('/research/sweep', { method: 'POST', json: { grid } })
}

/** GET /research/sweep/{job_id}/status — 輪詢 */
export function getSweepStatus(jobId: string): Promise<ApiResult<SweepJob>> {
  return http<SweepJob>(`/research/sweep/${encodeURIComponent(jobId)}/status`)
}
