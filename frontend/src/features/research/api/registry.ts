/*
 * Research zone — strategy registry（shipped：GET /strategies，ADR-028 取代 /presets）。
 * 回傳所有已註冊策略的 name / title / description / config_schema（JSON-schema）。
 * 注意：與 GET /research/strategies（runs ledger 投影 roster）不同——此為策略「型錄」。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface StrategyInfo {
  name: string
  title: string
  description: string
  config_schema: Record<string, unknown>
}

/** GET /strategies — 策略型錄（New Run 的 strategy 下拉來源）。 */
export function listStrategyRegistry(): Promise<ApiResult<StrategyInfo[]>> {
  return http<StrategyInfo[]>('/strategies')
}
