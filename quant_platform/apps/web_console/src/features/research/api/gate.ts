/* GET /gate/spec — IS gate 硬門檻規格（shipped）。 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface GateCriterion {
  key: string
  op: string
  threshold: number
  kind: 'edge' | 'health' | string
  label: string
}
export interface GateSpec {
  criteria: GateCriterion[]
}

export function getGateSpec(): Promise<ApiResult<GateSpec>> {
  return http<GateSpec>('/gate/spec')
}
