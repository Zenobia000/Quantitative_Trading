/*
 * Monitor-zone server-state hooks — thin typed wrappers over useEndpoint.
 * Each hits a real /monitor/* endpoint; pages render four states (loading/error/
 * pending/data). Endpoints that the paper daemon feeds (equity/positions/signals/
 * fills/kpi) return real telemetry; aggregate ones (fleet/risk) are
 * typed-empty `pending` until their producers land — pages light up automatically.
 */
import { useQuery } from '@tanstack/react-query'
import { useEndpoint } from '@/hooks/useEndpoint'
import { http } from '@/services/http'
import { ttlToMs } from '@/services/queryClient'
import type { ApiResult } from '@/types/domain'

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
export interface FleetRow {
  strategy_id: string
  equity: number
  cash: number
  open_positions: number
  portfolio_heat: number | null
  last_update: string
}
export interface PortfolioSummary {
  n_strategies?: number
  total_equity?: number
  total_open_positions?: number
}

export const useFleet = () => useEndpoint<FleetRow[]>('/monitor/fleet', 60)
export const usePortfolioSummary = () => useEndpoint<PortfolioSummary>('/monitor/portfolio-summary', 60)
export const useRiskMetrics = () => useEndpoint<Record<string, unknown>>('/monitor/risk/metrics', 30)

// ---- run board (A2) -------------------------------------------------------
export interface BoardRow {
  run_id: string
  strategy: string
  engine: string
  stocks: string[]
  is_start: string | null
  is_end: string | null
  status: string // running | done | failed（run_persist / run-batch 鏡射）
  gate_status: string | null // 審判庭 verdict；in-flight 為 null
  gate_summary: string | null
  metrics: Record<string, number> | null
  created_at: string | null
}
// 看板要「活」：10s 輪詢（useEndpoint 無 refetchInterval，故直接組 useQuery）。
// staleTime 由 meta.ttl 驅動（board 回 ttl=5，doc 25 §5.1 / A2），fallback 5s。
export const useRunsBoard = () =>
  useQuery<ApiResult<BoardRow[]>>({
    queryKey: ['endpoint', '/monitor/board'],
    queryFn: () => http<BoardRow[]>('/monitor/board'),
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 5),
    refetchInterval: 10_000,
  })

// ---- deferred display endpoints now wired --------------------------------
// 這些端點已註冊但回 typed-empty PENDING（meta.data_source==='pending'）；用 QueryState
// 走四態，producer 上線即自動點亮（M4）。view-model 依端點語意取最小合理欄位（openapi
// 為泛型 Envelope，data 無型別）。

// Perf A —— 基準對比曲線 / 月報酬
export interface BenchmarkPoint {
  t: string
  strategy: number
  benchmark: number
}
export interface MonthlyReturn {
  month: string
  return_pct: number
}
export const usePerfBenchmark = () => useEndpoint<BenchmarkPoint[]>('/monitor/performance/benchmark', 300)
export const usePerfMonthly = () => useEndpoint<MonthlyReturn[]>('/monitor/performance/monthly', 300)

// Positions B —— 產業配置 / 集中度 / 即時報價
export interface IndustryAllocation {
  industry: string
  weight: number
}
export interface Concentration {
  hhi?: number
  top5_weight?: number
  n_holdings?: number
}
export interface PriceQuote {
  stock_id: string
  price: number
  as_of?: string
}
export const usePosIndustry = () => useEndpoint<IndustryAllocation[]>('/monitor/positions/industry-allocation', 300)
export const usePosConcentration = () => useEndpoint<Concentration>('/monitor/positions/concentration', 300)
export const usePosPrices = () => useEndpoint<PriceQuote[]>('/monitor/positions/prices', 60)

// Signals C —— 訊號漏斗 / 時間軸
export interface FunnelStage {
  stage: string
  count: number
}
export interface TimelinePoint {
  t: string
  signals: number
  submitted: number
}
export const useSignalsFunnel = () => useEndpoint<FunnelStage[]>('/monitor/signals/funnel', 30)
export const useSignalsTimeline = () => useEndpoint<TimelinePoint[]>('/monitor/signals/timeline', 300)

// Risk D —— MaxDD 趨勢 / 熔斷事件
export interface MddPoint {
  t: string
  drawdown: number
}
export interface RiskEvent {
  event_time: string
  kind: string
  severity: string
  detail: string
}
export const useRiskMddTrend = () => useEndpoint<MddPoint[]>('/monitor/risk/mdd-trend', 60)
export const useRiskEvents = () => useEndpoint<RiskEvent[]>('/monitor/risk/events', 30)

// Fleet —— 相關性矩陣
export interface Correlation {
  axes: string[]
  z: number[][]
}
export const useCorrelation = () => useEndpoint<Correlation>('/monitor/correlation', 300)
