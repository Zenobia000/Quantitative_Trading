/* POST /runs — 提交一次 IS run（shipped）。body 型別取自 OpenAPI 生成（禁手寫形狀）。 */
import { http } from '@/services/http'
import type { components } from '@/types/api.gen'
import type { ApiResult } from '@/types/domain'

export type RunCreateRequest = components['schemas']['RunCreateRequest']

export function createRun(body: RunCreateRequest): Promise<ApiResult<{ run_id?: string } & Record<string, unknown>>> {
  return http('/runs', { method: 'POST', json: body })
}
