/*
 * 單張 scorecard ledger cell —— category 燈號 + 各指標 pass/warn/fail 計數 + 一鍵跳對應 sheet tab。
 * 整張卡 not_available（如 panel 策略的 Win Rate）→ 誠實顯示「無法產出 + 原因」，不留無說明佔位（UX 驗收 #3）。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { Scorecard } from '../../api/reportViewer'
import { isCardUnavailable, statusMark, statusTone, type MetricStatus } from '../../lib/scorecardStatus'

/** 計各狀態數量（渲染「3 pass · 1 warn」摘要列）。 */
function tally(metrics: Scorecard['metrics']): Partial<Record<MetricStatus, number>> {
  const out: Partial<Record<MetricStatus, number>> = {}
  for (const m of metrics) out[m.status] = (out[m.status] ?? 0) + 1
  return out
}

const COUNT_ORDER: MetricStatus[] = ['pass', 'warn', 'fail', 'not_available', 'not_applicable', 'missing']

export function ScorecardCard({
  scorecard,
  active,
  onSelect,
}: {
  scorecard: Scorecard
  active: boolean
  onSelect: () => void
}) {
  const { t } = useTranslation('research')
  const label = t(`reportViewer.scorecard.category.${scorecard.category}`, { defaultValue: scorecard.category })
  const unavailable = isCardUnavailable(scorecard.status)
  const counts = tally(scorecard.metrics)

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={active}
      data-testid={`scorecard-${scorecard.category}`}
      className={`flex min-h-[112px] flex-col border-b border-border bg-surface p-3 text-left transition-colors lg:border-b-0 lg:border-r last:lg:border-r-0 ${
        active ? 'bg-input outline outline-1 outline-info' : 'hover:bg-row'
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-semibold uppercase tracking-[0.08em] text-text">{label}</span>
        <StatusBadge tone={statusTone(scorecard.status)}>
          <span aria-hidden>{statusMark(scorecard.status)}</span>
          <span>{t(`reportViewer.status.${scorecard.status}`)}</span>
        </StatusBadge>
      </div>

      {unavailable ? (
        <p className="text-xs text-text-muted">{scorecard.note ?? t('reportViewer.scorecard.notAvailableCard')}</p>
      ) : (
        <div className="mt-auto flex flex-wrap gap-1.5 font-mono text-[11px] text-text-secondary tabular">
          {COUNT_ORDER.filter((s) => counts[s]).map((s) => (
            <span key={s} className="inline-flex items-center gap-1">
              <span aria-hidden>{statusMark(s)}</span>
              {counts[s]} {t(`reportViewer.status.${s}`)}
            </span>
          ))}
        </div>
      )}
    </button>
  )
}
