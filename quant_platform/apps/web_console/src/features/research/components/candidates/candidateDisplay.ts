/*
 * Candidate Pool 純顯示 / 決策邏輯（無 React、無 i18n → 可獨立單元測試）。
 * tone 映射本地維護（本頁不碰 status.json / displayMap.ts；label 走 research namespace）。
 * 決策套用為不可變（回傳新 Candidate），對齊 CLAUDE.md 不可變性硬約束。
 */
import type {
  Candidate,
  CandidateDecision,
  CandidateState,
  DecisionAction,
  LiveOosRecommendation,
  ScorecardStatus,
} from '../../api/candidates'

export type Tone = 'gain' | 'loss' | 'warning' | 'error' | 'muted'

/** UI 動作四選（契約決策動作的前端投影）。 */
export type CandidateAction = 'keep' | 'archive' | 'rerun' | 'select_live_oos'

/** 候選狀態 → tone（色）。text label 一律另附（雙編碼硬約束 #6），tone 撞色可接受。 */
const CANDIDATE_STATE_TONE: Record<CandidateState, Tone> = {
  draft: 'muted',
  triaged: 'muted',
  promising: 'gain',
  weak: 'warning',
  negative: 'loss',
  data_issue: 'error',
  live_oos_selected: 'gain',
  live_oos_running: 'gain',
  live_oos_done: 'muted',
  deploy_blocked: 'error',
  deployable: 'gain',
  archived: 'muted',
}

export function candidateStateTone(state: string): Tone {
  return CANDIDATE_STATE_TONE[state as CandidateState] ?? 'muted'
}

/** scorecard 每維狀態 → tone。 */
const SCORECARD_TONE: Record<ScorecardStatus, Tone> = {
  pass: 'gain',
  warn: 'warning',
  fail: 'loss',
  not_available: 'muted',
  missing: 'muted',
  not_applicable: 'muted',
}

export function scorecardTone(status: string): Tone {
  return SCORECARD_TONE[status as ScorecardStatus] ?? 'muted'
}

/** scorecard 狀態的形狀字符（形狀 + 色的雙編碼，避免只靠顏色傳達狀態）。 */
const SCORECARD_GLYPH: Record<ScorecardStatus, string> = {
  pass: '●',
  warn: '◐',
  fail: '✕',
  not_available: '–',
  missing: '–',
  not_applicable: '–',
}

export function scorecardGlyph(status: string): string {
  return SCORECARD_GLYPH[status as ScorecardStatus] ?? '–'
}

/** Live-OOS 建議 → tone（資訊 chip 用）。 */
const RECOMMENDATION_TONE: Record<LiveOosRecommendation, Tone> = {
  eligible: 'gain',
  not_recommended: 'warning',
  blocked: 'error',
}

export function recommendationTone(reco: string): Tone {
  return RECOMMENDATION_TONE[reco as LiveOosRecommendation] ?? 'muted'
}

/** 部署級判決 → tone（資訊態；Candidate Pool 不放 promote 動作）。 */
export function truthVerdictTone(verdict: string | null | undefined): Tone {
  switch (verdict) {
    case 'REAL':
      return 'gain'
    case 'PAPER_WATCH':
      return 'warning'
    case 'REJECTED':
      return 'error'
    default:
      return 'muted'
  }
}

/** report_pack_ref（reports/research_runs/<run_id>/manifest.json）→ runId，供 Report Viewer 連結。 */
export function runIdFromReportRef(ref: string | null | undefined): string | null {
  if (!ref) return null
  const m = ref.match(/research_runs\/([^/]+)\//)
  return m ? m[1] : null
}

const TERMINAL_OR_QUEUED: CandidateState[] = [
  'archived',
  'live_oos_selected',
  'live_oos_running',
  'live_oos_done',
]

/** 該動作在此候選當前狀態下是否可用（disabled 判斷 + hint）。 */
export function actionEnabled(c: Candidate, action: CandidateAction): boolean {
  switch (action) {
    case 'keep':
      return c.state !== 'archived'
    case 'archive':
      return c.state !== 'archived'
    case 'rerun':
      return true
    case 'select_live_oos':
      // 已在隊列 / 已封存 / 資料問題 → 不可勾選 Live OOS。
      return !TERMINAL_OR_QUEUED.includes(c.state) && c.state !== 'data_issue'
  }
}

/**
 * 此動作是否強制填理由（契約 §6.3 override 規則）：
 * - archive 一律必填
 * - select_live_oos 且 recommendation ≠ eligible → override，必填
 * - keep / rerun / eligible 的 select → 免填
 */
export function reasonRequired(c: Candidate, action: CandidateAction): boolean {
  if (action === 'archive') return true
  if (action === 'select_live_oos') return c.live_oos_recommendation !== 'eligible'
  return false
}

/** 動作套用後的目標狀態。 */
function nextState(c: Candidate, action: CandidateAction): CandidateState {
  switch (action) {
    case 'keep':
      return 'promising'
    case 'archive':
      return 'archived'
    case 'rerun':
      return c.state // 重跑評測：狀態不變（等新 EvaluationResult 回填）
    case 'select_live_oos':
      return 'live_oos_selected'
  }
}

/** 記錄到 decisions[] 的契約動作名（非 eligible 的勾選記為 override_select）。 */
function decisionActionOf(c: Candidate, action: CandidateAction): DecisionAction {
  if (action === 'select_live_oos') {
    return c.live_oos_recommendation === 'eligible' ? 'select_live_oos' : 'override_select'
  }
  return action
}

let localSeq = 0

/**
 * 不可變套用一個決策：回傳帶新 state + 追加 decision 的新 Candidate。
 * fixture 模式的本地樂觀更新用（不寫後端）。
 */
export function applyDecision(
  c: Candidate,
  action: CandidateAction,
  reason: string | undefined,
  now: string = new Date().toISOString(),
): Candidate {
  const to = nextState(c, action)
  const decision: CandidateDecision = {
    decision_id: `local_${(localSeq += 1)}`,
    candidate_id: c.candidate_id,
    at: now,
    actor: 'operator',
    action: decisionActionOf(c, action),
    from_state: c.state,
    to_state: to,
    reason: reason && reason.trim() ? reason.trim() : null,
    evaluation_ref: c.latest_evaluation_id,
  }
  return { ...c, state: to, decisions: [...c.decisions, decision] }
}
