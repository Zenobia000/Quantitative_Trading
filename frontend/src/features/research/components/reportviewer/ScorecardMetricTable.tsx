/*
 * scorecard 指標明細表 —— 每指標一列：狀態燈（pass/warn/fail/not_available）+ 原始值 + 門檻（op value）
 * + 出處/原因。不是只有數字（UX 驗收 #2）。not_available 指標誠實顯示原因，不留無說明佔位（UX 驗收 #3）。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { Scorecard, ScorecardMetric } from '../../api/reportViewer'
import { fmtMetricValue, fmtThreshold, statusMark, statusTone } from '../../lib/scorecardStatus'

function MetricRow({ metric }: { metric: ScorecardMetric }) {
  const { t } = useTranslation('research')
  const threshold = fmtThreshold(metric.op, metric.threshold, metric.unit)
  const detail = metric.reason ?? metric.note ?? null
  return (
    <tr className="border-b border-border/40 align-top">
      <td className="py-1.5 pr-3">
        <StatusBadge tone={statusTone(metric.status)}>
          <span aria-hidden>{statusMark(metric.status)}</span>
          <span>{t(`reportViewer.status.${metric.status}`)}</span>
        </StatusBadge>
      </td>
      <td className="py-1.5 pr-3 text-text">{metric.label}</td>
      <td className="py-1.5 pr-3 font-mono tabular text-text">{fmtMetricValue(metric.value, metric.unit)}</td>
      <td className="py-1.5 pr-3 font-mono tabular text-text-secondary">{threshold ?? '—'}</td>
      <td className="py-1.5 text-xs text-text-muted">{detail ?? '—'}</td>
    </tr>
  )
}

export function ScorecardMetricTable({ scorecard }: { scorecard: Scorecard }) {
  const { t } = useTranslation('research')
  return (
    <div className="overflow-x-auto">
      {scorecard.note && (
        <p className="mb-2 rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-xs text-text-muted">
          {scorecard.note}
        </p>
      )}
      <table className="w-full min-w-[520px] text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-muted">
            <th className="py-1.5 pr-3 font-medium">{t('reportViewer.scorecard.statusCol')}</th>
            <th className="py-1.5 pr-3 font-medium">{t('reportViewer.scorecard.metricCol')}</th>
            <th className="py-1.5 pr-3 font-medium">{t('reportViewer.scorecard.valueCol')}</th>
            <th className="py-1.5 pr-3 font-medium">{t('reportViewer.scorecard.thresholdCol')}</th>
            <th className="py-1.5 font-medium">{t('reportViewer.scorecard.reasonCol')}</th>
          </tr>
        </thead>
        <tbody>
          {scorecard.metrics.map((m) => (
            <MetricRow key={m.id} metric={m} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
