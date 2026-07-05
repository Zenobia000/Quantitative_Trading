/*
 * 月報酬熱圖 —— 純 CSS grid（不引圖表庫）。年×月 cell 依正負 + 幅度上色
 * （正綠 --gain / 負紅 --loss-aaa，AAA 對比：底色低濃度 + 粗體同色文字）+ 年合計欄。
 * cell null = 無觀察月 → 破折號、不著色（與真實 0.0% 平月讀法不同，GOAL #8）。
 * basis 揭露：日期為重建 business-day 近似。著色純函式在 lib/reportViz。
 */
import { useTranslation } from 'react-i18next'
import type { MonthlyReturns } from '../api/report'
import { cellSign, fmtPct, heatAlphaPct } from '../lib/reportViz'

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)

function cellStyle(value: number | null): { backgroundColor?: string } {
  const sign = cellSign(value)
  if (sign === 'none') return {}
  const varName = sign === 'pos' ? '--gain' : '--loss-aaa'
  return { backgroundColor: `color-mix(in srgb, var(${varName}) ${heatAlphaPct(value)}%, transparent)` }
}

function cellTextClass(value: number | null): string {
  const sign = cellSign(value)
  if (sign === 'pos') return 'text-gain'
  if (sign === 'neg') return 'text-loss-aaa'
  return 'text-text-muted'
}

export function MonthlyHeatmap({
  monthly,
  note,
}: {
  monthly: MonthlyReturns | null | undefined
  note: string | null | undefined
}) {
  const { t } = useTranslation('research')

  const hasData = !!monthly && monthly.years.length > 0
  if (!hasData) {
    return (
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-2 text-[18px] font-semibold">{t('report.monthly.title')}</h2>
        <p className="rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-sm text-text-muted">
          {note ?? t('report.monthly.empty')}
        </p>
      </section>
    )
  }

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 flex flex-wrap items-baseline gap-2">
        <h2 className="text-[18px] font-semibold">{t('report.monthly.title')}</h2>
        <span className="text-[11px] text-text-muted">{t('report.monthly.basisHint')}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-center font-mono text-[11px] tabular">
          <thead>
            <tr className="text-text-muted">
              <th className="px-1.5 py-1 text-left font-medium">{t('report.monthly.year')}</th>
              {MONTHS.map((m) => (
                <th key={m} className="px-1.5 py-1 font-medium">
                  {m}
                </th>
              ))}
              <th className="px-1.5 py-1 font-medium text-text-secondary">
                {t('report.monthly.annual')}
              </th>
            </tr>
          </thead>
          <tbody>
            {monthly.years.map((year, r) => {
              const row = monthly.matrix[r] ?? []
              const annual = monthly.annual[r] ?? null
              return (
                <tr key={year}>
                  <th className="px-1.5 py-1 text-left font-medium text-text-secondary">{year}</th>
                  {MONTHS.map((m, c) => {
                    const value = row[c] ?? null
                    return (
                      <td
                        key={m}
                        data-sign={cellSign(value)}
                        style={cellStyle(value)}
                        className={`px-1.5 py-1 ${cellTextClass(value)}`}
                        title={value == null ? undefined : fmtPct(value)}
                      >
                        {value == null ? '—' : fmtPct(value, 1)}
                      </td>
                    )
                  })}
                  <td
                    data-sign={cellSign(annual)}
                    style={cellStyle(annual)}
                    className={`px-1.5 py-1 font-semibold ${cellTextClass(annual)}`}
                  >
                    {annual == null ? '—' : fmtPct(annual, 1)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
