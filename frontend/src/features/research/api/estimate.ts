/* GET /runs/estimate — sweep 提交前估算（shipped，真接）。 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface Estimate {
  n_configs: number
  est_minutes: number
  axes: Record<string, number>
}

/** grid：{box_period:"40,60,80", ...}（逗號列）→ {n_configs, est_minutes, axes} */
export function getEstimate(grid: Record<string, string>): Promise<ApiResult<Estimate>> {
  const query: Record<string, string> = {}
  for (const [k, v] of Object.entries(grid)) if (v.trim()) query[k] = v.trim()
  return http<Estimate>('/runs/estimate', { query })
}
