/* Home cockpit hooks。 */
import { useQuery } from '@tanstack/react-query'
import { getRecent, getResearchStatus } from '../api/home'
import { useEndpoint } from '@/hooks/useEndpoint'
import { ttlToMs } from '@/services/queryClient'

export const useResearchStatus = () =>
  useQuery({ queryKey: ['home', 'research-status'], queryFn: getResearchStatus, staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300) })

export const useRecent = () =>
  useQuery({ queryKey: ['home', 'recent'], queryFn: getRecent, staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300) })

/**
 * Cross-zone system health（ADR-021 §6.4 aggregation）。後端目前回 typed-empty
 * PENDING（M4 producer 未落地）；欄位在 producer 上線時填入，前端零改碼自動點亮。
 * 前端據此渲染 Command Center 狀態帶 —— pending 時顯示誠實空態，絕不假造。
 */
export interface SystemHealth {
  risk_lock?: string // CLEAR / HALT / …
  mode?: string // PAPER / LIVE
  data_bundle?: string // READY / PENDING / STALE
  broker?: string // ONLINE / OFFLINE
}
export const useSystemHealth = () => useEndpoint<SystemHealth>('/home/system-health', 300)

export interface HomeFleetRow {
  strategy_id: string
  equity?: number
  open_positions?: number
  status?: string
}
export const useHomeFleet = () => useEndpoint<HomeFleetRow[]>('/home/fleet', 300)
