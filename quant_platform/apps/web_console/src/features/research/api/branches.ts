/*
 * Branch experiments 資料源（Goal 9，/research/branches）—— 顯式 parent→child 策略迭代血統。
 *
 * 手寫窄化 view-model（沿用 candidates.ts / simulation.ts 慣例：後端泛型 Envelope → 前端精確承載，
 * 不碰 api.gen.ts）。契約真相源 dev_docs/contracts/branch_experiment.example.json + README §14。
 *
 * 無 fixture fallback：分支實驗是 live-only 功能（無打包範例）；後端未上線 / 錯誤一律以 ApiError
 * 上拋，由 section / dialog 呈現 error 態（不靜默、不假資料）。
 */
import { http } from '@/services/http'

/** 分支來源（never LLM）—— 模擬 fork / 手動 / 報告發現。 */
export type BranchOrigin = 'simulation' | 'manual' | 'report_finding'

/** 分支狀態：draft（已建未評測）→ evaluated（已回填 evaluation_id）。 */
export type BranchStatus = 'draft' | 'evaluated'

/** 一筆 config 變更（from 由後端從 parent config 解析，前端只需帶 key + to）。 */
export interface ConfigDeltaEntry {
  key: string
  from?: unknown
  to: unknown
}

/** 一筆分支實驗記錄（GET/POST /research/branches 的 data payload）。 */
export interface BranchExperiment {
  branch_id: string
  parent_evaluation_id: string
  parent_run_id: string
  strategy: string
  profile: string
  origin: BranchOrigin
  note: string | null
  config_delta: ConfigDeltaEntry[]
  branch_config: Record<string, unknown>
  /** true 才可評測（至少改了一個真 config 欄位）；overlay-only 分支為 false。 */
  applies_to_rerun: boolean
  created_at: string
  evaluation_id: string | null
  status: BranchStatus
  evaluated_at?: string
}

/** compare 表一列（parent/branch 值 + delta + 方向）。 */
export interface BranchCompareRow {
  metric: string
  lower_is_better: boolean
  parent: number | null
  branch: number | null
  delta: number | null
  change: 'improved' | 'worsened' | 'flat'
}

/** compare 決策（Sharpe tie-break + 可讀 reasons）。 */
export interface BranchDecision {
  verdict: 'branch_better' | 'parent_better' | 'inconclusive'
  parent_label: string | null
  branch_label: string | null
  reasons: string[]
}

/** GET /research/branches/{id}/compare 的 data payload。 */
export interface BranchCompare {
  branch_id: string
  strategy: string
  parent_evaluation_id: string
  parent_run_id: string
  branch_evaluation_id: string | null
  branch_run_id: string | null
  config_delta: ConfigDeltaEntry[]
  branch_evaluated: boolean
  metrics: BranchCompareRow[]
  decision: BranchDecision | null
}

/** POST /research/branches 的請求體。 */
export interface CreateBranchBody {
  parent_evaluation_id: string
  config_delta: ConfigDeltaEntry[]
  origin: BranchOrigin
  note?: string
  profile?: string
}

/** 列該策略 / 該 parent 的分支（newest-first；後端 #176 分頁）。 */
export async function fetchBranches(params: {
  strategy?: string
  parent_evaluation_id?: string
}): Promise<BranchExperiment[]> {
  const res = await http<BranchExperiment[]>('/research/branches', {
    query: { strategy: params.strategy, parent_evaluation_id: params.parent_evaluation_id },
  })
  return res.data ?? []
}

/** Fork 一個分支（404 未知 parent / 422 非法 delta key/值 → ApiError）。 */
export async function createBranch(body: CreateBranchBody): Promise<BranchExperiment> {
  const res = await http<BranchExperiment>('/research/branches', { method: 'POST', json: body })
  return res.data
}

/** 跑分支 config（quick_triage 同步）→ 回填 evaluation_id（404 / 409 overlay-only → ApiError）。 */
export async function evaluateBranch(branchId: string): Promise<BranchExperiment> {
  const res = await http<BranchExperiment>(
    `/research/branches/${encodeURIComponent(branchId)}/evaluate`,
    { method: 'POST' },
  )
  return res.data
}

/** 分支 vs parent headline delta 表 + 決策（404 → ApiError）。 */
export async function fetchBranchCompare(branchId: string): Promise<BranchCompare> {
  const res = await http<BranchCompare>(
    `/research/branches/${encodeURIComponent(branchId)}/compare`,
  )
  return res.data
}
