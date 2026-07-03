/*
 * What-if 模擬資料源（Goal 8，POST /research/simulate）—— 研究沙盤，唯讀不持久化。
 *
 * 手寫窄化 view-model（沿用 reportViewer.ts / series.ts 慣例：後端泛型 Envelope → 前端精確承載，
 * 不碰 api.gen.ts）。契約真相源 dev_docs/contracts/simulation_result.example.json + README §13。
 *
 * 刻意「不進 react-query 快取」：模擬是即算即棄的沙盤，快取化會讓過期參數殘留污染 Report Viewer。
 * 呼叫端以本地 state 持有結果、按「執行模擬」時才打（見 SimulationPanel），不 keystroke 打 API。
 */
import { http } from '@/services/http'

/** 送出的 what-if 參數（對齊後端 SimulationRequest 邊界；越界由後端 422）。 */
export interface SimulationRequest {
  run_id: string
  cost_multiplier: number
  slippage_bps: number
  stop_loss_pct: number | null
  take_profit_pct: number | null
  capacity_scale: number
}

/** 一個指標空間（portfolio-equity / trade-population）的 before/after/delta；不可行時 available=false。 */
export interface MetricSpace {
  available: boolean
  reason: string | null
  space: string
  before: Record<string, number> | null
  after: Record<string, number> | null
  deltas: Record<string, number> | null
}

/** 逐參數可行性審計（applied / noop / not_available + 原因）。 */
export interface PerParam {
  param: string
  requested: number | null
  space: string
  applied: boolean
  status: 'applied' | 'noop' | 'not_available'
  reason?: string
}

/** 建議分支（config delta 描述；actionable=false → fork 按鈕 disabled，待 Goal 9）。 */
export interface BranchSuggestion {
  label: string
  description: string
  config_delta: { key: string; from: number | null; to: number | null; note?: string }[]
  actionable: boolean
  actionable_reason: string
}

/** POST /research/simulate 的 data payload（契約 §13.3）。 */
export interface SimulationResult {
  schema_version: string
  run_id: string
  strategy: string | null
  research_only: boolean
  applied_params: SimulationRequest
  portfolio_metrics: MetricSpace
  trade_metrics: MetricSpace
  affected_trades_count: number
  per_param: PerParam[]
  branch_suggestion: BranchSuggestion | null
  data_gaps: { field: string; reason: string }[]
}

/** 打後端跑一次 what-if。錯誤（404 未知 run / 422 越界 / 網路）以 ApiError 上拋，由 panel 呈現。 */
export async function runSimulation(req: SimulationRequest): Promise<SimulationResult> {
  const res = await http<SimulationResult>('/research/simulate', { method: 'POST', json: req })
  return res.data
}

/** portfolio-equity 空間指標顯示順序（fraction/ratio 各自格式化見 SimulationPanel）。 */
export const PORTFOLIO_METRIC_KEYS = [
  'total_return',
  'cagr',
  'sharpe',
  'sortino',
  'calmar',
  'max_drawdown',
  'ulcer_index',
  'volatility',
] as const

/** trade-population 空間指標顯示順序。 */
export const TRADE_METRIC_KEYS = [
  'n_trades',
  'win_rate',
  'avg_trade_return',
  'total_trade_return',
  'profit_factor',
  'avg_hold',
] as const

/** ratio 型指標（不 ×100）；其餘 portfolio 指標視為 fraction。 */
const RATIO_KEYS = new Set(['sharpe', 'sortino', 'calmar', 'ulcer_index'])
/** count 型 trade 指標（整數，不 ×100）。 */
const COUNT_KEYS = new Set(['n_trades'])
/** ratio 型 trade 指標。 */
const TRADE_RATIO_KEYS = new Set(['profit_factor', 'avg_hold'])

/** 指標值 → 顯示字串（fraction ×100 加 %；ratio 兩位小數；count 整數；null → 破折號）。 */
export function fmtSimValue(key: string, value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—'
  if (COUNT_KEYS.has(key)) return String(Math.round(value))
  if (RATIO_KEYS.has(key) || TRADE_RATIO_KEYS.has(key)) return value.toFixed(2)
  return `${(value * 100).toFixed(2)}%`
}

/** 「越低越好」的指標（回撤 / ulcer / 波動）——delta 為負才是改善。 */
const LOWER_IS_BETTER = new Set(['max_drawdown', 'ulcer_index', 'volatility'])
/** 方向中性、不著色的指標（交易數 / 平均持有）。 */
const NEUTRAL_KEYS = new Set(['n_trades', 'avg_hold'])

/** delta → 語意色調（gain 改善 / loss 惡化 / neutral 不著色）。方向依指標好壞含義而非單純正負。 */
export function deltaTone(key: string, value: number | null | undefined): 'gain' | 'loss' | 'neutral' {
  if (value == null || !Number.isFinite(value) || value === 0 || NEUTRAL_KEYS.has(key)) return 'neutral'
  const goodness = LOWER_IS_BETTER.has(key) ? -value : value
  return goodness > 0 ? 'gain' : 'loss'
}

/** delta → 顯示字串（帶正負號）。 */
export function fmtSimDelta(key: string, value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—'
  if (COUNT_KEYS.has(key)) {
    const n = Math.round(value)
    return `${n >= 0 ? '+' : ''}${n}`
  }
  if (RATIO_KEYS.has(key) || TRADE_RATIO_KEYS.has(key)) {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`
  }
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
}
