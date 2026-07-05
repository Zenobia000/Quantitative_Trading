/*
 * Run-Report v1 視覺化純函式（無 DOM / 無 canvas，可在 jsdom 單元測試）。
 * DSR 標尺定位、月報酬熱圖 cell 著色、守門準則評估、business-day 索引重建 —— 集中於此，
 * 讓元件只管呈現、純計算可對手算 oracle 驗證（同 lib/candleTransform 慣例）。
 */
import type { Tone } from '@/i18n/displayMap'

/** DSR 標尺定值域與刻度（真相源 validation.two_stage_gate：DSR_MIN=0.95 / PAPER_WATCH_DSR_MIN=0.90）。 */
export const DSR_SCALE_MIN = 0.85
export const DSR_SCALE_MAX = 1.0
/** PAPER_WATCH 下界（進觀察艙門檻）。 */
export const DSR_TICK_PAPER = 0.9
/** REAL 下界（可部署門檻）。 */
export const DSR_TICK_REAL = 0.95

/**
 * DSR 值 → 標尺左偏移百分比 [0,100]（超出定值域夾邊，永不溢出）。
 * 例：0.85→0、0.925→50、1.00→100。
 */
export function dsrToPercent(dsr: number, min = DSR_SCALE_MIN, max = DSR_SCALE_MAX): number {
  const span = max - min
  if (span <= 0) return 0
  const p = ((dsr - min) / span) * 100
  return Math.min(100, Math.max(0, p))
}

/** DSR band → StatusBadge tone（REAL 綠 / PAPER_WATCH 琥珀 / REJECTED 紅 / 其餘中性）。 */
export function bandTone(band: string | null | undefined): Tone {
  switch (band) {
    case 'REAL':
      return 'gain'
    case 'PAPER_WATCH':
      return 'warning'
    case 'REJECTED':
      return 'loss'
    default:
      return 'muted'
  }
}

/** 熱圖 cell 正負向（null / 非有限 / 剛好 0 → 'none'，不著色；著色僅正負）。 */
export type CellSign = 'pos' | 'neg' | 'none'
export function cellSign(value: number | null | undefined): CellSign {
  if (value == null || !Number.isFinite(value) || value === 0) return 'none'
  return value > 0 ? 'pos' : 'neg'
}

/**
 * 熱圖 cell 背景著色濃度（color-mix 用百分比 12–60%）。
 * 依 |報酬| / cap 線性，cap 預設 10%（單月 10% 已屬強訊號）。null → 0（無底色）。
 */
export function heatAlphaPct(value: number | null | undefined, cap = 0.1): number {
  if (value == null || !Number.isFinite(value) || value === 0 || cap <= 0) return 0
  const intensity = Math.min(1, Math.abs(value) / cap)
  return Math.round(12 + intensity * 48)
}

/**
 * 守門準則評估：metric 值 op threshold → pass/fail；metric 缺失或非有限 → null（誠實未知，不亮燈）。
 * op 對齊後端 strategies.protocol GateCriterion.op（>= / > / <= / < / == / !=）。
 */
export function evalCriterion(
  value: number | null | undefined,
  op: string,
  threshold: number,
): boolean | null {
  if (value == null || !Number.isFinite(value)) return null
  switch (op) {
    case '>=':
      return value >= threshold
    case '>':
      return value > threshold
    case '<=':
      return value <= threshold
    case '<':
      return value < threshold
    case '==':
      return value === threshold
    case '!=':
      return value !== threshold
    default:
      return null
  }
}

/** 小數比例 → 帶號百分比字串；null / 非有限 → 破折號（誠實無資料）。 */
export function fmtPct(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

/**
 * 由 is_start 起算的 length-n business-day ISO 索引（Mon–Fri，跳週末，無假日曆）。
 * 對齊後端 runs_report `pd.date_range(freq="B")`——v1 序列 sidecar 不存日期索引，
 * equity 曲線 x 軸與 oos_start 對位皆以此近似重建（basis 已於 UI 揭露）。
 * 無效 is_start → 空陣列。
 */
export function reconstructBusinessDays(isStart: string, n: number): string[] {
  const out: string[] = []
  const d = new Date(`${isStart}T00:00:00Z`)
  if (Number.isNaN(d.getTime())) return out
  while (out.length < n) {
    const day = d.getUTCDay()
    if (day !== 0 && day !== 6) out.push(d.toISOString().slice(0, 10))
    d.setUTCDate(d.getUTCDate() + 1)
  }
  return out
}
