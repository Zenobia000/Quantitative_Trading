/*
 * 回撤事件表 —— top-5 最深回撤（後端已排序、已切 5）。
 * 欄：深度 / 峰值 / 谷底 / 回復 / 持續(bar)。未回復 → 回復欄破折號、depth 仍計（peak→last-bar）。
 * 有日期標籤用日期，無（run 缺 window）退回 bar index（誠實：純位置永遠精確）。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { DrawdownEvent } from '../api/report'
import { fmtPct } from '../lib/reportViz'

/** 日期優先、退回 bar index（#idx）；皆無 → 破折號。 */
function mark(date: string | null, idx: number | null): string {
  if (date) return date
  if (idx != null) return `#${idx}`
  return '—'
}

export function DrawdownEventsTable({ events }: { events: DrawdownEvent[] | null | undefined }) {
  const { t } = useTranslation('research')

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <h2 className="mb-2 text-[18px] font-semibold">{t('report.drawdown.title')}</h2>
      {!events || events.length === 0 ? (
        <p className="rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-sm text-text-muted">
          {t('report.drawdown.empty')}
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="py-1.5 pr-3 font-medium">{t('report.drawdown.depth')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('report.drawdown.peak')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('report.drawdown.trough')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('report.drawdown.recovery')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('report.drawdown.duration')}</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={i} className="border-b border-border/40">
                <td className="py-1.5 pr-3">
                  <StatusBadge tone="loss">-{fmtPct(e.depth)}</StatusBadge>
                </td>
                <td className="py-1.5 pr-3 font-mono tabular text-text-secondary">
                  {mark(e.peak_date, e.peak_idx)}
                </td>
                <td className="py-1.5 pr-3 font-mono tabular text-text-secondary">
                  {mark(e.trough_date, e.trough_idx)}
                </td>
                <td className="py-1.5 pr-3 font-mono tabular text-text-secondary">
                  {e.recovered ? mark(e.recovery_date, e.recovery_idx) : t('report.drawdown.unrecovered')}
                </td>
                <td className="py-1.5 pr-3 font-mono tabular text-text">{e.duration_bars}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
