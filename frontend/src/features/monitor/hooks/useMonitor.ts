/*
 * Monitor-zone server-state hooks — thin typed wrappers over useEndpoint.
 * Each hits a real /monitor/* endpoint; pages render four states (loading/error/
 * pending/data). Endpoints that the paper daemon feeds (equity/positions/signals/
 * fills/kpi) return real telemetry; aggregate ones (fleet/strategies/risk) are
 * typed-empty `pending` until their producers land — pages light up automatically.
 */
import { useEndpoint } from '@/hooks/useEndpoint'

export interface EquityPoint {
  t: string
  equity: number
  drawdown: number | null
}
export interface PerfKpi {
  current_equity?: number
  total_return?: number
  cagr?: number
  sharpe?: number
  max_drawdown?: number
  calmar?: number
  n_points?: number
}
export interface PositionRow {
  stock_id: string
  quantity: number
  entry_price: number
  stop_loss: number | null
  opened_at: string
  strategy_id: string
}
export interface SignalRow {
  signal_time: string
  strategy_id: string
  stock_id: string
  action: string
  priority: number
  submitted: boolean
}
export interface FillRow {
  created_at: string
  stock_id: string
  side: string
  quantity: number
  price: number | null
  status: string
}

export const usePerfKpi = () => useEndpoint<PerfKpi>('/monitor/performance/kpi', 300)
export const usePerfEquity = () => useEndpoint<EquityPoint[]>('/monitor/performance/equity', 300)
export const usePositions = () => useEndpoint<PositionRow[]>('/monitor/positions/snapshot', 60)
export const useSignals = () => useEndpoint<SignalRow[]>('/monitor/signals', 30)
export const useFills = () => useEndpoint<FillRow[]>('/monitor/fills', 300)
export const useFleet = () => useEndpoint<unknown[]>('/monitor/fleet', 60)
export const useStrategies = () => useEndpoint<unknown[]>('/monitor/strategies', 60)
export const useRiskMetrics = () => useEndpoint<Record<string, unknown>>('/monitor/risk/metrics', 30)
