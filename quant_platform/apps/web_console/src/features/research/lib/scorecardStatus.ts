/*
 * Report-Viewer 純函式：scorecard 指標狀態 → tone/符號、verdict label → tone、severity → tone。
 * 無 DOM，可在 jsdom 單測（同 lib/reportViz 慣例）。契約狀態集見 dev_docs/contracts/README.md §4.1：
 * status ∈ pass|warn|fail|missing|not_applicable|not_available；severity ∈ info|block_live_oos|block_deploy。
 */
import type { Tone } from '@/i18n/displayMap'

/** 契約 §4.1 每指標狀態集（含整張卡的 category 狀態，共用同一集合）。 */
export type MetricStatus =
  | 'pass'
  | 'warn'
  | 'fail'
  | 'missing'
  | 'not_applicable'
  | 'not_available'

/** 契約 §3 severity 分級（取代單一 binary verdict）。 */
export type Severity = 'info' | 'warn' | 'block_live_oos' | 'block_deploy'

/** 狀態 → StatusBadge tone（pass 綠 / warn 琥珀 / fail 紅 / 其餘中性——誠實未知不亮警報）。 */
export function statusTone(status: MetricStatus): Tone {
  switch (status) {
    case 'pass':
      return 'gain'
    case 'warn':
      return 'warning'
    case 'fail':
      return 'error'
    default:
      // missing / not_applicable / not_available：一律中性（不是失敗，是「無法評估」）。
      return 'muted'
  }
}

/** 狀態 → 燈號符號（附文字雙編碼，GOAL 硬約束 #6；不只靠顏色）。 */
export function statusMark(status: MetricStatus): string {
  switch (status) {
    case 'pass':
      return '✓'
    case 'warn':
      return '△'
    case 'fail':
      return '✗'
    case 'not_available':
      return '⊘'
    case 'not_applicable':
      return '–'
    default:
      return '○' // missing
  }
}

/** 整張卡是否「完全無法產出」（category 狀態 not_available → 誠實顯示原因，不留空佔位）。 */
export function isCardUnavailable(status: MetricStatus): boolean {
  return status === 'not_available'
}

/** verdict.label（Promising/Strong/Weak/Negative/…）→ tone。未知標籤退回 muted。 */
export function verdictTone(label: string | null | undefined): Tone {
  switch ((label ?? '').toLowerCase()) {
    case 'promising':
    case 'strong':
    case 'deployable':
      return 'gain'
    case 'weak':
    case 'marginal':
      return 'warning'
    case 'negative':
    case 'fail':
    case 'failed':
    case 'rejected':
      return 'loss'
    default:
      return 'muted'
  }
}

/** severity → tone（block_deploy 紅 / block_live_oos 琥珀 / 其餘中性——讀作分級非全紅警報）。 */
export function severityTone(severity: string | null | undefined): Tone {
  switch (severity) {
    case 'block_deploy':
      return 'error'
    case 'block_live_oos':
    case 'warn':
      return 'warning'
    default:
      return 'muted'
  }
}

/**
 * truth_verdict（REAL/PAPER_WATCH/REJECTED/INCOMPLETE）→ DsrRuler band（REAL/PAPER_WATCH/REJECTED）。
 * INCOMPLETE / 未知 → null（不捏造 band，DsrRuler 走空態）。
 */
export function truthVerdictToBand(truthVerdict: string | null | undefined): string | null {
  switch (truthVerdict) {
    case 'REAL':
    case 'PAPER_WATCH':
    case 'REJECTED':
      return truthVerdict
    default:
      return null
  }
}

/**
 * 指標值 → 顯示字串。fraction/percentage → ×100 加 %；其餘照原值（整數不補小數）。
 * null / 非有限 → 破折號（誠實無資料，不捏 0）。
 */
export function fmtMetricValue(value: number | null | undefined, unit: string | null): string {
  if (value == null || !Number.isFinite(value)) return '—'
  if (unit === 'fraction' || unit === 'percentage') return `${(value * 100).toFixed(2)}%`
  if (unit === 'count' || unit === 'bars') return Number.isInteger(value) ? String(value) : value.toFixed(1)
  if (unit === 'currency') return value.toLocaleString()
  return Number.isInteger(value) ? String(value) : value.toFixed(3)
}

/** 門檻字串「op value」（如「> 0.18」）；無門檻 → null（呼叫端渲染破折號）。 */
export function fmtThreshold(op: string | null, threshold: number | null, unit: string | null): string | null {
  if (op == null || threshold == null) return null
  const v = unit === 'fraction' || unit === 'percentage' ? `${(threshold * 100).toFixed(1)}%` : String(threshold)
  return `${op} ${v}`
}
