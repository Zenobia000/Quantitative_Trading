/*
 * Research zone — Candidate Pool（Goal 6，fixture-first）。
 * 先打 `GET /research/candidates`（envelope client）；端點尚未上線（Goal 4 平行開發中）→
 * 任何 ApiError（404 / NETWORK / 後端錯誤）fallback 到打包的契約範例
 * `../fixtures/candidate_pool.json`，並回傳 source 供 UI 明示資料來源。
 *
 * 型別為手寫窄化 view-model（對齊 dev_docs/contracts/candidate_pool.example.json），
 * 不碰 api.gen.ts。決策 POST 在 fixture 模式下僅本地樂觀更新（見 hooks/useCandidatePool）。
 */
import { http, ApiError } from '@/services/http'
import type { ApiMeta } from '@/types/domain'
import fixture from '../fixtures/candidate_pool.json'

/** 候選狀態機（契約 §6.1，12 態）。 */
export type CandidateState =
  | 'draft'
  | 'triaged'
  | 'promising'
  | 'weak'
  | 'negative'
  | 'data_issue'
  | 'live_oos_selected'
  | 'live_oos_running'
  | 'live_oos_done'
  | 'deploy_blocked'
  | 'deployable'
  | 'archived'

/** 五維 scorecard 摘要燈的每維狀態（契約 §4.1）。 */
export type ScorecardStatus =
  | 'pass'
  | 'warn'
  | 'fail'
  | 'not_available'
  | 'missing'
  | 'not_applicable'

export type ScorecardKey = 'profitability' | 'risk' | 'risk_adjusted' | 'win_rate' | 'liquidity'

export const SCORECARD_KEYS: ScorecardKey[] = [
  'profitability',
  'risk',
  'risk_adjusted',
  'win_rate',
  'liquidity',
]

export type ScorecardSummary = Record<ScorecardKey, ScorecardStatus>

/** Live-OOS 建議（契約 §6.3 override 規則據此判斷是否必填理由）。 */
export type LiveOosRecommendation = 'eligible' | 'not_recommended' | 'blocked'

/** 部署級判決（契約 verdict.truth_verdict；只作資訊態呈現，非 Candidate Pool 主動作）。 */
export type TruthVerdict = 'REAL' | 'PAPER_WATCH' | 'REJECTED' | 'INCOMPLETE'

/** 決策事件動作（契約 §6.3；append-only）。 */
export type DecisionAction =
  | 'auto_label'
  | 'keep'
  | 'archive'
  | 'rerun'
  | 'select_live_oos'
  | 'override_select'
  | 'mark_data_issue'
  | 'unarchive'

export interface CandidateHeadline {
  sharpe: number | null
  oos_holdout_sharpe: number | null
  cagr: number | null
  max_drawdown: number | null
  dsr?: number | null
  pbo?: number | null
  trade_win_rate?: number | null
  trades: number | null
  avg_turnover: number | null
  survivorship_clean: boolean
}

export interface CandidateDecision {
  decision_id: string
  candidate_id: string
  at: string
  actor: 'system' | 'operator'
  action: DecisionAction
  from_state: CandidateState
  to_state: CandidateState
  reason: string | null
  evaluation_ref: string
  queue_ref?: string
}

export interface Candidate {
  candidate_id: string
  strategy: string
  hypothesis: string
  created_at: string
  state: CandidateState
  latest_evaluation_id: string
  latest_profile: string
  latest_label: string
  latest_truth_verdict: TruthVerdict | null
  live_oos_recommendation: LiveOosRecommendation
  scorecard_summary: ScorecardSummary
  headline: CandidateHeadline
  report_pack_ref: string
  next_action: string
  note?: string
  decisions: CandidateDecision[]
}

export type CandidateSource = 'api' | 'fixture'

export interface CandidatePoolResult {
  candidates: Candidate[]
  meta: ApiMeta
  /** 'api' = 後端 live；'fixture' = 打包契約範例（決策僅本地）。 */
  source: CandidateSource
}

interface CandidatePoolEnvelopeShape {
  data: Candidate[]
  meta: ApiMeta
}

/**
 * 抓候選池：先打後端，失敗即 fallback 打包 fixture。
 * 回傳 `source` 讓 UI 明示資料來源（fixture 模式 badge）。
 */
export async function fetchCandidatePool(): Promise<CandidatePoolResult> {
  try {
    const res = await http<Candidate[]>('/research/candidates')
    return { candidates: res.data ?? [], meta: res.meta, source: 'api' }
  } catch (e) {
    // 端點尚未上線（Goal 4）→ 打包契約範例。非 ApiError（非預期）才向上拋。
    if (!(e instanceof ApiError)) throw e
    const env = fixture as unknown as CandidatePoolEnvelopeShape
    return { candidates: env.data, meta: { ...env.meta, data_source: 'fixture' }, source: 'fixture' }
  }
}
