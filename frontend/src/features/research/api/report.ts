/*
 * Research zone — Run-Report v1 聚合端點（shipped：GET /runs/{id}/report）+ notebook 下載。
 *
 * 形狀說明：OpenAPI 的 RunReportData 各 block 以 `extra='allow'` 鬆散字典建模
 * （{[k]:unknown}），刻意讓「無來源」欄位誠實回 null；故此處手寫精確 view-model
 * 承載（同 series.ts / candles.ts 慣例：後端泛型 Envelope → 前端窄化）。不改 api.gen.ts。
 * 真相源為 backtest_platform/api/routers/runs_report.py 的 assembly。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

/** 策略宣告的一條守門準則（strategies.protocol GateCriterion）。 */
export interface GateCriterion {
  key: string
  /** 比較運算子：>= / > / <= / < / == / != */
  op: string
  threshold: number
  /** 'edge'（優勢門檻）| 'guard'（護欄）*/
  kind: string
  label: string
}

/** 觀察艙艙位——唯一被持久化的真偽閘證據（watch_registry）。未進艙 → 整塊 null。 */
export interface TruthGateBerth {
  /** 進艙時的 verdict DSR（band 由此推定）；未知 → null（不捏造 band）。 */
  verdict_dsr: number | null
  /** REAL | PAPER_WATCH | REJECTED（由 verdict_dsr 分帶）；null → 尚無 DSR。 */
  band: string | null
  state?: string
  enrolled_on?: string
  expiry_date?: string
  days_remaining?: number
  observed_trading_days?: number
  source?: string
}

export interface ReportVerdict {
  /** IS 守門判定 PASS/FAIL/INCOMPLETE。 */
  gate_status: string | null
  gate_summary?: unknown
  /** 策略宣告的守門準則（未知策略 / 未宣告 → null）。 */
  criteria: GateCriterion[] | null
  validation?: unknown
  /** 真偽閘（觀察艙）證據；未進艙 → null。 */
  truth_gate: TruthGateBerth | null
}

export interface RunWindow {
  is_start: string | null
  is_end: string | null
}

/** TRUTH_GATE 封存邊界（策略 research_config 宣告時才有）。 */
export interface TruthGateWindow {
  is_start: string
  oos_start: string
  is_end: string
}

export interface ReportSegments {
  run_window: RunWindow | null
  truth_gate_window: TruthGateWindow | null
}

/** 年×月報酬矩陣（cell null = 無觀察月；basis 揭露日期為重建 business-day）。 */
export interface MonthlyReturns {
  years: number[]
  matrix: (number | null)[][]
  annual: number[]
  basis?: string
}

/** 一次回撤事件（峰→谷→回復）；未回復 → recovery_* null、recovered=false。 */
export interface DrawdownEvent {
  peak_idx: number
  trough_idx: number
  recovery_idx: number | null
  peak_date: string | null
  trough_date: string | null
  recovery_date: string | null
  /** 正分數 (peak-trough)/peak。 */
  depth: number
  duration_bars: number
  recovered: boolean
}

export interface CostSensitivity {
  sharpe: number | null
  slippage_sharpe: number | null
}

/** GET /runs/{id}/report 的一次性聚合（每個無來源欄位誠實 null）。 */
export interface RunReport {
  run_id: string
  verdict: ReportVerdict | null
  segments: ReportSegments | null
  monthly_returns: MonthlyReturns | null
  monthly_returns_note: string | null
  drawdown_events: DrawdownEvent[] | null
  cost_sensitivity: CostSensitivity | null
}

/** GET /runs/{id}/report — Run-Report 頁一次載齊（verdict / segments / monthly / dd / cost）。 */
export function getRunReport(runId: string): Promise<ApiResult<RunReport>> {
  return http<RunReport>(`/runs/${encodeURIComponent(runId)}/report`)
}

const BASE = import.meta.env.VITE_API_BASE ?? '' // 對齊 services/http：dev 走 vite proxy（相對路徑）

/**
 * GET /runs/{id}/notebook 的下載連結（Open-in-notebook）。
 * 回傳與 http client 同源的絕對/相對 URL，供 <a href download> 直接取用。
 */
export function notebookHref(runId: string): string {
  return `${BASE}/runs/${encodeURIComponent(runId)}/notebook`
}
