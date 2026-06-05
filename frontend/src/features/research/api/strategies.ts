/*
 * Research zone — strategies（shipped：GET /research/strategies，runs ledger projection）。
 * data 為 generic envelope；view-model 對齊後端 _project_strategies 輸出。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface StrategyRow {
  strategy_id: string
  version: string
  best_kpi: Record<string, number> | Record<string, unknown>
  validation_status: 'is_pass' | 'is_fail' | 'draft' | string
  stage: string
  runs_count: number
}

export function listStrategies(params?: { page?: number; limit?: number }): Promise<ApiResult<StrategyRow[]>> {
  return http<StrategyRow[]>('/research/strategies', { query: params })
}
