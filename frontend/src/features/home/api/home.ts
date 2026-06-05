/* Home cockpit BFF（/home/*）。research-status / recent 真聚合；fleet / system-health pending。 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export interface ResearchStatus {
  total_runs: number
  latest_gate_status: string | null
  is_gate_blocker: string | null
  trials: number | null
  dsr: number | null
}
export interface RecentItem {
  type: string
  run_id?: string
  preset?: string
  gate_status?: string
}

export const getResearchStatus = (): Promise<ApiResult<ResearchStatus>> => http<ResearchStatus>('/home/research-status')
export const getRecent = (): Promise<ApiResult<RecentItem[]>> => http<RecentItem[]>('/home/recent')
export const getHomeFleet = (): Promise<ApiResult<unknown[]>> => http<unknown[]>('/home/fleet')
export const getSystemHealth = (): Promise<ApiResult<Record<string, unknown>>> =>
  http<Record<string, unknown>>('/home/system-health')
