/*
 * Research zone — compare（shipped：GET /runs/compare?baseline=&run_ids=a,b,c）。
 * 回應為「物件」（非陣列）：{baseline_id, metric_keys, sign_consistent, rankings, comparisons[]}。
 * 形狀取自 OpenAPI 生成型別（禁手寫）。
 */
import { http } from '@/services/http'
import type { components } from '@/types/api.gen'
import type { ApiResult } from '@/types/domain'

export type CompareReport = components['schemas']['CompareReportData']
export type CompareRow = components['schemas']['RunComparisonRow']

/** GET /runs/compare — baseline 為基準、run_ids 為比較子集（前端多選）。 */
export function getCompare(params: { baseline?: string; run_ids?: string[] }): Promise<ApiResult<CompareReport>> {
  const query: Record<string, string | undefined> = { baseline: params.baseline }
  if (params.run_ids && params.run_ids.length > 0) query.run_ids = params.run_ids.join(',')
  return http<CompareReport>('/runs/compare', { query })
}
