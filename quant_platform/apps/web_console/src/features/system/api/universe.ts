/*
 * POST /system/universe/build（ADR-032 async）+ GET /system/universe/build/{id}/status。
 * body 型別取自 OpenAPI 生成（`npm run gen:api`）—— 禁手寫形狀（doc 25）。
 * 鏡射 ingest 的 async job + 輪詢慣例（8.H.6）。
 */
import { http } from '@/services/http'
import type { components } from '@/types/api.gen'
import type { ApiResult } from '@/types/domain'
import type { JobRef } from './ingest'

export type UniverseBuildBody = components['schemas']['UniverseBuildRequest']

/** 建置工作的結果酬載（run_build_universe 摘要）。 */
export interface UniverseBuildResult {
  strategy?: string
  n_symbols?: number
  n_alive?: number
  n_delisted?: number
  n_ingested_ok?: number
  n_ingested_failed?: number
  manifest_path?: string
}

export type UniverseJobRef = Omit<JobRef, 'result'> & { result?: UniverseBuildResult | null }

export function triggerUniverseBuild(body: UniverseBuildBody): Promise<ApiResult<UniverseJobRef>> {
  return http('/system/universe/build', { method: 'POST', json: body })
}

export function getUniverseBuildStatus(jobId: string): Promise<ApiResult<UniverseJobRef>> {
  return http(`/system/universe/build/${encodeURIComponent(jobId)}/status`)
}
