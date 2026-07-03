/*
 * Report-Viewer 資料源（fixture-first，可無縫切換）。
 * 先試 GET /research/evaluations/{id}（envelope http client）；後端 Goal 3/4 尚未落地時
 * （404 / 網路失敗 / 非 envelope 回應）fallback 到 bundled fixture（從 dev_docs/contracts 複製到
 * ../fixtures，不 import repo 根外路徑）。UI 依 `source` 明示 data source（真 API vs fixture）。
 *
 * 形狀為手寫窄化 view-model（沿用 series.ts / report.ts 慣例：後端泛型 Envelope → 前端精確承載）；
 * 不碰 api.gen.ts。真相源為 dev_docs/contracts/evaluation_result.example.json + README.md §4。
 */
import { ApiError, http } from '@/services/http'
import type { ApiMeta } from '@/types/domain'
import type { MetricStatus } from '../lib/scorecardStatus'
import type { Candidate } from './candidates'
import evaluationFixture from '../fixtures/evaluation_result.example.json'

/** IS/OOS 分段窗（deployment_strict 才有 oos_start）。 */
export interface EvalWindow {
  is_start: string
  oos_start?: string | null
  is_end: string
}

/** 回測宇集（survivorship-clean 為部署級硬證據）。 */
export interface EvalUniverse {
  symbols_count: number
  bundle_ref: string
  survivorship_clean: boolean
  note?: string
}

/** 建議下一步（取代單一 binary verdict；action + confidence + 理由列）。 */
export interface EvalRecommendation {
  action: string
  confidence: string
  reasons: string[]
}

export interface EvalVerdict {
  /** 對人 label：Promising / Weak / Negative / …。 */
  label: string
  /** 真偽閘判定 REAL / PAPER_WATCH / REJECTED / INCOMPLETE；triage profile 無真偽閘 → null。 */
  truth_verdict: string | null
  /**
   * Live-OOS 建議（eligible / not_recommended / blocked）。真後端 EvaluationResult 的
   * verdict 帶此欄（契約超集）；bundled fixture 無此欄 → optional。Report Viewer 決策列據此
   * 判斷 Select Live OOS 是否需 override 理由。
   */
  live_oos_recommendation?: string | null
  recommendation: EvalRecommendation
}

/** 五維 scorecard 內一條指標（每指標帶 pass/warn/fail/not_available 燈 + 原始值 + 門檻 + 出處）。 */
export interface ScorecardMetric {
  id: string
  label: string
  value: number | null
  unit: string
  threshold: number | null
  op: string | null
  status: MetricStatus
  severity: string
  source_module: string | null
  /** pass/warn 時的補充說明。 */
  note?: string
  /** not_available / fail 時的原因（誠實揭露，不留無說明佔位）。 */
  reason?: string
}

/** 一張 scorecard（Profitability / Risk / Risk-Adjusted / Win Rate / Liquidity）。 */
export interface Scorecard {
  category: string
  status: MetricStatus
  /** 整張卡 not_available 時的原因（如 Win Rate for panel strategy）。 */
  note?: string
  metrics: ScorecardMetric[]
}

/** deployment_strict hard-fail 燈號一條（truth-gate CheckResult）。 */
export interface GateCheck {
  metric: string
  value: number | boolean | null
  threshold: number | boolean | null
  op: string
  status: MetricStatus
  severity: string
  reason: string
}

export interface EvalLineage {
  config_hash: string
  config_hash_source?: string
  params: Record<string, unknown>
  engine: string
  bundle_ref: string
  n_trials: number
  git_sha: string | null
  git_sha_status?: string
  git_sha_reason?: string
}

export interface EvalDataGap {
  field: string
  reason: string
}

/** GET /research/evaluations/{id} 的 data payload（契約 §4）。每個無來源欄位誠實 null / not_available。 */
export interface EvaluationResult {
  schema_version: string
  evaluation_id: string
  run_id: string
  strategy: string
  profile: string
  profile_version: string
  created_at: string
  window: EvalWindow
  universe: EvalUniverse
  verdict: EvalVerdict
  headline_metrics: Record<string, number | null>
  scorecards: Scorecard[]
  checks: GateCheck[]
  sizing: { position_size: number; reason: string }
  lineage: EvalLineage
  /** report-pack 清單（真後端頂層帶此契約超集欄位；窄化層不消費，僅標型別以免視為 any）。 */
  report_pack?: unknown
  report_pack_ref: string
  data_gaps: EvalDataGap[]
}

/** 資料來源標記（UI 明示真 API vs bundled fixture）。 */
export type DataSource = 'api' | 'fixture'

export interface EvaluationLoad {
  data: EvaluationResult
  meta: ApiMeta
  source: DataSource
}

/** 後端未落地時觸發 fixture fallback 的錯誤碼（404 / 網路 / 非 envelope 502-HTML）。 */
const FALLBACK_CODES = new Set(['NOT_FOUND', 'NETWORK', 'INTERNAL'])

/** report_pack_ref（reports/research_runs/<run_id>/manifest.json）→ run_id。 */
function runIdFromReportRef(ref: string | null | undefined): string | null {
  if (!ref) return null
  const m = ref.match(/research_runs\/([^/]+)\//)
  return m ? m[1] : null
}

/**
 * 把 URL 上的 id 解成後端 evaluation ledger 的鍵（`eval_<strategy>_<profile>_<run_id>`）。
 *
 * store 以 `evaluation_id` 為鍵（`research.evaluation.store.get_evaluation`）。兩個入口帶的 id 語意不同：
 * - Candidate Pool 卡：直接帶 `candidate.latest_evaluation_id`（`eval_…` 前綴）→ 原樣打。
 * - Run Report「開啟完整報告」：僅有 run_id（run ledger 不帶 profile / evaluation_id）→ 以候選池
 *   `report_pack_ref` 反查（其含 run_id），命中則改用該候選的 `latest_evaluation_id`。
 *
 * 反查失敗（候選端點不可達 / 無對應候選）→ 回原 id，交由後續 GET 收 404 → fixture fallback。
 */
export async function resolveEvaluationId(id: string): Promise<string> {
  if (id.startsWith('eval_')) return id
  try {
    const res = await http<Candidate[]>('/research/candidates')
    const match = (res.data ?? []).find((c) => runIdFromReportRef(c.report_pack_ref) === id)
    return match?.latest_evaluation_id ?? id
  } catch {
    return id
  }
}

/**
 * 載入一份 evaluation。先解 id（run_id → evaluation_id，見 {@link resolveEvaluationId}），再打真 API；
 * 後端 Goal 3/4 未落地（404/網路/非 envelope）→ 回 bundled fixture。
 * 其餘錯誤（401/422/…）照拋，讓上層渲染 error 態（不誤把真錯誤蓋成 fixture）。
 */
export async function getEvaluation(id: string): Promise<EvaluationLoad> {
  try {
    const evaluationId = await resolveEvaluationId(id)
    const res = await http<EvaluationResult>(
      `/research/evaluations/${encodeURIComponent(evaluationId)}`,
    )
    return { data: res.data, meta: res.meta, source: 'api' }
  } catch (e) {
    if (e instanceof ApiError && FALLBACK_CODES.has(e.code)) {
      return {
        data: evaluationFixture as unknown as EvaluationResult,
        meta: { data_source: 'fixture', ttl: 300 },
        source: 'fixture',
      }
    }
    throw e
  }
}
