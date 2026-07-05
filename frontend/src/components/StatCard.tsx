/*
 * StatCard — 單一 KPI / evidence cell（合併原本散落三處的 Kpi/KpiCard：
 * home/HomePage、research/RunReportPage、monitor/components）。
 * 數字清楚、label 弱化；可選 hint 供「以佐證取信」的出處說明
 * （coverage / reproduce），而非炫耀式行銷。遵 ops console：1px border、無陰影、tabular-nums。
 *
 * value 可為數字（配 pct/signed 自動格式化 + 漲跌雙編碼 ↑↓）或任意 ReactNode（如 StatusBadge）。
 */
import type { ReactNode } from 'react'

export function StatCard({
  label,
  value,
  pct,
  signed,
  hint,
}: {
  label: string
  value: ReactNode
  /** 數值為小數比例，×100 顯示 % */
  pct?: boolean
  /** 帶正負號 → 套漲跌色 + ↑↓（色盲雙編碼） */
  signed?: boolean
  /** 出處 / 佐證說明（如 as-of 日期、樣本數），弱化顯示 */
  hint?: ReactNode
}) {
  const isNum = typeof value === 'number'
  const num = isNum ? (value as number) : null
  // KPI 大數字須達 AAA(7:1)：loss 用 --loss-aaa (#fca5a5, 9.2:1)，非 AA 的 --loss。
  const tone = signed && num != null ? (num >= 0 ? 'text-gain' : 'text-loss-aaa') : 'text-text'
  const arrow = signed && num != null ? (num >= 0 ? '↑ ' : '↓ ') : ''
  const shown: ReactNode = isNum
    ? pct
      ? `${arrow}${(num! * 100).toFixed(2)}%`
      : `${arrow}${Number.isInteger(num) ? num : num!.toFixed(2)}`
    : value

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="text-xs text-text-muted">{label}</div>
      <div className={`mt-1.5 font-mono text-2xl tabular tracking-tight ${tone}`}>{shown}</div>
      {hint != null && <div className="mt-1 text-[11px] text-text-muted">{hint}</div>}
    </div>
  )
}
