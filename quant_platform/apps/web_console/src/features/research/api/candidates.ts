/*
 * Research zone — Candidate Pool。
 * 先打 `GET /research/candidates`（envelope client，端點已上線）；任何 ApiError
 * （404 / NETWORK / 後端錯誤）才 fallback 到打包的契約範例
 * `../fixtures/candidate_pool.json` 作為離線韌性，並回傳 source 供 UI 明示資料來源。
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
  /** 最新評測若來自分支實驗（Goal 9），帶其血統（branch_id / parent 連結）；否則 null。 */
  branch_origin?: { branch_id: string; parent_evaluation_id: string; parent_run_id: string; origin: string } | null
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
    // 端點失敗（404 / 網路）→ 離線韌性回打包契約範例。非 ApiError（非預期）才向上拋。
    if (!(e instanceof ApiError)) throw e
    const env = fixture as unknown as CandidatePoolEnvelopeShape
    return { candidates: env.data, meta: { ...env.meta, data_source: 'fixture' }, source: 'fixture' }
  }
}

// --------------------------------------------------------------------------- //
// mutations（api 模式真寫入；fixture 模式由頁面本地樂觀 overlay 承接，不打這裡）    //
// --------------------------------------------------------------------------- //

/** POST /research/candidates/{id}/decision 的請求體（契約 §6.3 決策事件）。 */
export interface DecisionRequestBody {
  /** 決策端點僅收 keep / archive / rerun / mark_data_issue / unarchive（select 走 select-live-oos）。 */
  action: 'keep' | 'archive' | 'rerun' | 'mark_data_issue' | 'unarchive'
  /** override / archive 稽核理由（後端 422 缺 reason）。 */
  reason?: string
  /** keep 目標標籤（promising / weak / negative）；後端 keep 必帶。 */
  label?: 'promising' | 'weak' | 'negative'
}

/** POST /research/candidates/{id}/select-live-oos 的請求體（契約 §6.3 選入 Live OOS）。 */
export interface SelectLiveOosRequestBody {
  /** override / 非 eligible 選取的必填理由。 */
  reason?: string
  /** blocked 候選需 override=true（否則 409）；非 eligible 亦以 override_select 記錄。 */
  override?: boolean
  /** 觀察型別（預設 paper_replay）。 */
  observation_kind?: string
}

/** live-OOS 佇列項（select-live-oos 成功回傳；此處只需寬鬆型別供 mutation 回傳）。 */
export interface LiveOosQueueItem {
  queue_id: string
  candidate_id: string
  strategy: string
  [key: string]: unknown
}

/**
 * 追加一筆候選決策（keep / archive / rerun / mark_data_issue / unarchive）。
 * 後端 state-machine 驗證：400 illegal transition / 422 缺 reason / 404 未知候選 —— 一律以
 * {@link ApiError} 上拋（由 mutation onError 呈現，不靜默）。回傳 append 的決策事件。
 */
export async function postCandidateDecision(
  candidateId: string,
  body: DecisionRequestBody,
): Promise<CandidateDecision> {
  const res = await http<CandidateDecision>(
    `/research/candidates/${encodeURIComponent(candidateId)}/decision`,
    { method: 'POST', json: body },
  )
  return res.data
}

/**
 * 選一個候選進 Live OOS：入列 + 追加決策。
 * 後端：blocked 未 override → 409；非 eligible 缺 reason → 422；非法轉移 → 400 —— 皆以
 * {@link ApiError} 上拋。回傳入列的 queue item。
 */
export async function postSelectLiveOos(
  candidateId: string,
  body: SelectLiveOosRequestBody,
): Promise<LiveOosQueueItem> {
  const res = await http<LiveOosQueueItem>(
    `/research/candidates/${encodeURIComponent(candidateId)}/select-live-oos`,
    { method: 'POST', json: body },
  )
  return res.data
}

/**
 * 把 mutation 錯誤攤成可讀訊息（顯示在 dialog / 頁面 banner，不靜默）。
 * ApiError：後端 message（如 "illegal transition"）+ 400 的 detail.hint 補述；
 * 非 ApiError：Error.message；其餘：泛用字串。i18n 由呼叫端以 {detail} 插值包裝。
 */
export function describeMutationError(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail as { hint?: unknown } | null | undefined
    const hint = detail && typeof detail.hint === 'string' ? detail.hint : null
    return hint ? `${err.message}（${hint}）` : err.message
  }
  if (err instanceof Error && err.message) return err.message
  return 'unknown error'
}
