/*
 * POST /system/ingest（8.H.6 async）+ GET /system/ingest/{id}/status。
 * NOTE: body 型別暫手定（後端 IngestRequest 為新端點）；待 `npm run gen:api`
 * 重生 api.gen.ts 後改用 components['schemas']['IngestRequest']（禁手寫形狀之 follow-up）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface IngestBody {
  symbols: string[]
  start: string // YYYY-MM-DD
  end: string
  source?: 'finlab' | 'finmind'
}

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
