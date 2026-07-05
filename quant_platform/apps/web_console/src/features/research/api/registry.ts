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

export interface StrategyPackageFile {
  path: string
  role: string
  present: boolean
}

export interface StrategyAsset {
  strategy: string
  package: string
  package_path: string
  files: StrategyPackageFile[]
  workflows: string[]
  endpoints: Record<string, string>
}

export interface StrategyOptimizationSchema {
  strategy: string
  config_schema: Record<string, unknown>
  optimization: {
    workflow: 'doe'
    grid: Record<string, unknown[]>
    n_configs: number
    is_start: string
    is_end: string
    symbols_count: number
    symbols_preview: string[]
  } | null
}

export interface WorkflowSubmit {
  job_id: string
  status: string
}

/** GET /strategies — 策略型錄（New Run 的 strategy 下拉來源）。 */
export function listStrategyRegistry(): Promise<ApiResult<StrategyInfo[]>> {
  return http<StrategyInfo[]>('/strategies')
}

/** GET /strategies/{strategy}/asset — Strategy Package descriptor（ADR-008）。 */
export function getStrategyAsset(strategy: string): Promise<ApiResult<StrategyAsset>> {
  return http<StrategyAsset>(`/strategies/${encodeURIComponent(strategy)}/asset`)
}

/** GET /strategies/{strategy}/optimization-schema — DOE grid read model（ADR-008）。 */
export function getStrategyOptimizationSchema(strategy: string): Promise<ApiResult<StrategyOptimizationSchema>> {
  return http<StrategyOptimizationSchema>(`/strategies/${encodeURIComponent(strategy)}/optimization-schema`)
}

/** POST /research/workflows/doe — submit DOE optimization with optional grid override. */
export function submitDoeWorkflow(body: {
  strategy: string
  overrides?: { grid?: Record<string, unknown[]> }
}): Promise<ApiResult<WorkflowSubmit>> {
  return http<WorkflowSubmit>('/research/workflows/doe', { method: 'POST', json: body })
}
