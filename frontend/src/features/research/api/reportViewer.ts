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
  /** 真偽閘判定 REAL / PAPER_WATCH / REJECTED / INCOMPLETE。 */
  truth_verdict: string
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

/**
 * 載入一份 evaluation。先打真 API，後端 Goal 3/4 未落地（404/網路/非 envelope）→ 回 bundled fixture。
 * 其餘錯誤（401/422/…）照拋，讓上層渲染 error 態（不誤把真錯誤蓋成 fixture）。
 */
export async function getEvaluation(id: string): Promise<EvaluationLoad> {
  try {
    const res = await http<EvaluationResult>(`/research/evaluations/${encodeURIComponent(id)}`)
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
