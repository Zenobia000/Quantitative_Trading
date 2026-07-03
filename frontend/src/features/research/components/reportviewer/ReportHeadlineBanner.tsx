/*
 * Headline banner（置頂）—— 首屏三答（UX 驗收 #1）：這是什麼 / 表現如何 / 建議下一步。
 * 復用 VerdictCard 概念（大 verdict badge）+ StatCard（headline 指標網格）。
 * 左：策略/run/profile/window/universe（是什麼）；中：verdict label + truth_verdict badge（表現如何）；
 * 右：recommendation.action + confidence + 理由列（下一步）。指標 null → StatCard 顯示破折號（誠實無資料）。
 */
import { useTranslation } from 'react-i18next'
import { StatCard } from '@/components/StatCard'
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

export function ReportHeadlineBanner({ result }: { result: EvaluationResult }) {
  const { t } = useTranslation('research')
  const { strategy, run_id, profile, window, universe, verdict, headline_metrics } = result
  const tone = verdictTone(verdict.label)
  const windowText = window.oos_start
    ? `${window.is_start} → ${window.is_end} · OOS ${window.oos_start}`
    : `${window.is_start} → ${window.is_end}`

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 這是什麼 */}
        <div>
          <div className="mb-1.5 text-xs text-text-muted">{t('reportViewer.banner.whatTitle')}</div>
          <div className="text-lg font-semibold">{strategy}</div>
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
        <div>
          <div className="mb-1.5 text-xs text-text-muted">{t('reportViewer.banner.performanceTitle')}</div>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-md border px-3 py-1 text-lg font-semibold ${BIG[tone]}`}
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
        <div>
          <div className="mb-1.5 text-xs text-text-muted">{t('reportViewer.banner.nextTitle')}</div>
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

      {/* headline 指標網格（RWD：mobile 2 欄 → 直向堆疊，無重疊） */}
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {HEADLINE.map((k) => (
          <StatCard
            key={k.key}
            label={t(k.labelKey)}
            value={num(headline_metrics[k.key]) ?? '—'}
            pct={k.pct}
            signed={k.signed}
          />
        ))}
      </div>
    </section>
  )
}
