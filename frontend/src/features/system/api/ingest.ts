/*
 * POST /system/ingest（8.H.6 async）+ GET /system/ingest/{id}/status。
 * body 型別取自 OpenAPI 生成（`npm run gen:api`）—— 禁手寫形狀（doc 25）。
 */
import { http } from '@/services/http'
import type { components } from '@/types/api.gen'
import type { ApiResult } from '@/types/domain'

export type IngestBody = components['schemas']['IngestRequest']

export interface JobRef {
  job_id: string
  status: string | null
  progress?: number | null
  result?: { requested?: number; ok?: string[]; failed?: string[] } | null
  error?: string | null
}

export function triggerIngest(body: IngestBody): Promise<ApiResult<JobRef>> {
  return http('/system/ingest', { method: 'POST', json: body })
}

export function getIngestStatus(jobId: string): Promise<ApiResult<JobRef>> {
  return http(`/system/ingest/${encodeURIComponent(jobId)}/status`)
}
