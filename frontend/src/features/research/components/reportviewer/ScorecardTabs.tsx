/*
 * Sheet tabs —— 每 scorecard 一個 tab，展開該維度明細（ScorecardMetricTable，fixture 保證有料）。
 * 相關維度另複用既有序列元件（接 shipped /runs/{id}/report · /equity，真 run 落地即點亮；
 * 此 evaluation fixture 未內含序列 → 顯示「已解釋的空態」，不留無說明佔位 UX 驗收 #3）：
 *   profitability → MonthlyHeatmap（時期穩定性）· risk → DrawdownEventsTable · risk_adjusted → ReportEquityChart。
 * activeCategory 由父層（與 ScorecardGrid 共享）控制 → 點卡即切 tab。
 */
import { useTranslation } from 'react-i18next'
import type { Scorecard } from '../../api/reportViewer'
import { useRunReport } from '../../hooks/useRunReport'
import { useRunEquity } from '../../hooks/useRunSeries'
import { ScorecardMetricTable } from './ScorecardMetricTable'
import { MonthlyHeatmap } from '../MonthlyHeatmap'
import { DrawdownEventsTable } from '../DrawdownEventsTable'
import { ReportEquityChart } from '../ReportEquityChart'
import { statusMark, statusTone } from '../../lib/scorecardStatus'
import { StatusBadge } from '@/components/StatusBadge'

/** 序列缺席時的「已解釋空態」（非無說明佔位）。 */
function SeriesNote({ text }: { text: string }) {
  return (
    <p className="mt-3 rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-xs text-text-muted">
      {text}
    </p>
  )
}

export function ScorecardTabs({
  scorecards,
  runId,
  activeCategory,
  onSelect,
}: {
  scorecards: Scorecard[]
  runId: string
  activeCategory: string
  onSelect: (category: string) => void
}) {
  const { t } = useTranslation('research')
  const reportQ = useRunReport(runId)
  const equityQ = useRunEquity(runId)
  const report = reportQ.data?.data

  const active = scorecards.find((sc) => sc.category === activeCategory) ?? scorecards[0]
  if (!active) return null

  const equity = equityQ.data?.data?.equity ?? []
  const drawdown = equityQ.data?.data?.drawdown ?? []
  const isStart = report?.segments?.run_window?.is_start ?? null
  const oosStart = report?.segments?.truth_gate_window?.oos_start ?? null

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <h2 className="mb-3 text-[18px] font-semibold">{t('reportViewer.sheets.title')}</h2>

      {/* tab 列（RWD：可橫向捲動，不重疊） */}
      <div role="tablist" className="mb-3 flex flex-wrap gap-1.5 overflow-x-auto">
        {scorecards.map((sc) => {
          const on = sc.category === active.category
          return (
            <button
              key={sc.category}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => onSelect(sc.category)}
              className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-sm transition-colors ${
                on ? 'border-text text-text' : 'border-border text-text-secondary hover:text-text'
              }`}
            >
              <StatusBadge tone={statusTone(sc.status)}>
                <span aria-hidden>{statusMark(sc.status)}</span>
              </StatusBadge>
              {t(`reportViewer.scorecard.category.${sc.category}`, { defaultValue: sc.category })}
            </button>
          )
        })}
      </div>

      {/* 明細表（fixture 保證有料） */}
      <ScorecardMetricTable scorecard={active} />

      {/* 相關維度序列（接真 run 即點亮；fixture 空態已解釋） */}
      {active.category === 'profitability' && (
        <div className="mt-3">
          <MonthlyHeatmap
            monthly={report?.monthly_returns}
            note={report?.monthly_returns_note ?? t('reportViewer.sheets.seriesNote')}
          />
        </div>
      )}
      {active.category === 'risk' && (
        <div className="mt-3">
          <DrawdownEventsTable events={report?.drawdown_events} />
        </div>
      )}
      {active.category === 'risk_adjusted' && (
        <div className="mt-3">
          <h3 className="mb-2 text-sm font-semibold">{t('reportViewer.sheets.equityTitle')}</h3>
          {equity.length > 0 ? (
            <ReportEquityChart equity={equity} drawdown={drawdown} isStart={isStart} oosStart={oosStart} />
          ) : (
            <SeriesNote text={t('reportViewer.sheets.seriesNote')} />
          )}
        </div>
      )}
    </section>
  )
}
