/*
 * Report headline ledger：首屏回答「這是什麼 / 表現如何 / 下一步」。
 * 使用 dense evidence cells，避免報告頁回到大卡片/hero 風格。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { Tone } from '@/i18n/displayMap'
import type { EvaluationResult } from '../../api/reportViewer'
import { verdictTone } from '../../lib/scorecardStatus'

const BIG: Record<Tone, string> = {
  gain: 'border-gain/50 text-gain',
  loss: 'border-loss/50 text-loss',
  warning: 'border-warning/50 text-warning',
  error: 'border-error/50 text-error',
  muted: 'border-border text-text-muted',
}

// headline 指標網格（契約 headline_metrics 鍵；百分比欄以小數傳、StatCard ×100）。
const HEADLINE: { key: string; labelKey: string; pct?: boolean; signed?: boolean }[] = [
  { key: 'cagr', labelKey: 'reportViewer.metrics.cagr', pct: true, signed: true },
  { key: 'sharpe', labelKey: 'reportViewer.metrics.sharpe' },
  { key: 'max_drawdown', labelKey: 'reportViewer.metrics.maxDrawdown', pct: true },
  { key: 'dsr', labelKey: 'reportViewer.metrics.dsr' },
  { key: 'oos_holdout_sharpe', labelKey: 'reportViewer.metrics.oosHoldoutSharpe' },
  { key: 'trades', labelKey: 'reportViewer.metrics.trades' },
]

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

function fmt(v: number | null, pct?: boolean): string {
  if (v == null) return '—'
  if (pct) return `${(v * 100).toFixed(2)}%`
  return Number.isInteger(v) ? String(v) : v.toFixed(2)
}

function HeadlineCell({
  label,
  value,
  pct,
  signed,
}: {
  label: string
  value: number | null
  pct?: boolean
  signed?: boolean
}) {
  const tone = signed && value != null ? (value >= 0 ? 'text-gain' : 'text-loss') : 'text-text'
  return (
    <div className="border border-border bg-base px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.14em] text-text-muted">{label}</div>
      <div className={`mt-1 font-mono text-[15px] tabular ${tone}`}>{fmt(value, pct)}</div>
    </div>
  )
}

export function ReportHeadlineBanner({ result }: { result: EvaluationResult }) {
  const { t } = useTranslation('research')
  const { strategy, run_id, profile, window, universe, verdict, headline_metrics } = result
  const tone = verdictTone(verdict.label)
  const windowText = window.oos_start
    ? `${window.is_start} → ${window.is_end} · OOS ${window.oos_start}`
    : `${window.is_start} → ${window.is_end}`

  return (
    <section className="mb-3 border border-border bg-panel">
      <div className="grid grid-cols-1 border-b border-border lg:grid-cols-[1.2fr_0.8fr_1fr]">
        <div className="border-b border-border p-3 lg:border-b-0 lg:border-r">
          <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">{t('reportViewer.banner.whatTitle')}</div>
          <div className="font-mono text-sm font-semibold text-text">{strategy}</div>
          <dl className="mt-1.5 space-y-0.5 font-mono text-xs text-text-secondary">
            <div>
              <span className="text-text-muted">{t('reportViewer.banner.profile')}: </span>
              <span className="text-text">{profile}</span>
            </div>
            <div>
              <span className="text-text-muted">{t('reportViewer.banner.run')}: </span>
              <span className="text-text">{run_id}</span>
            </div>
            <div>
              <span className="text-text-muted">{t('reportViewer.banner.window')}: </span>
              <span className="text-text">{windowText}</span>
            </div>
            <div>
              <span className="text-text-muted">{t('reportViewer.banner.universe')}: </span>
              <span className="text-text">{t('reportViewer.banner.symbols', { n: universe.symbols_count })}</span>
              {universe.survivorship_clean && (
                <span className="ml-1.5">
                  <StatusBadge tone="gain">
                    <span aria-hidden>✓</span>
                    {t('reportViewer.banner.survivorship')}
                  </StatusBadge>
                </span>
              )}
            </div>
          </dl>
        </div>

        {/* 表現如何 */}
        <div className="border-b border-border p-3 lg:border-b-0 lg:border-r">
          <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">{t('reportViewer.banner.performanceTitle')}</div>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center border px-3 py-1 font-mono text-sm font-semibold ${BIG[tone]}`}
            >
              {verdict.label}
            </span>
            <StatusBadge tone="muted">
              {t('reportViewer.banner.truthVerdict')}: {verdict.truth_verdict}
            </StatusBadge>
          </div>
          <p className="mt-2 text-xs text-text-secondary">
            {t('reportViewer.banner.confidence', { level: verdict.recommendation.confidence })}
          </p>
        </div>

        {/* 建議下一步 */}
        <div className="p-3">
          <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">{t('reportViewer.banner.nextTitle')}</div>
          <StatusBadge tone={tone}>{verdict.recommendation.action}</StatusBadge>
          <ul className="mt-2 space-y-1 text-xs text-text-secondary">
            {verdict.recommendation.reasons.map((r, i) => (
              <li key={i} className="flex gap-1.5">
                <span aria-hidden className="text-text-muted">
                  ·
                </span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3 xl:grid-cols-6">
        {HEADLINE.map((k) => (
          <HeadlineCell
            key={k.key}
            label={t(k.labelKey)}
            value={num(headline_metrics[k.key])}
            pct={k.pct}
            signed={k.signed}
          />
        ))}
      </div>
    </section>
  )
}
