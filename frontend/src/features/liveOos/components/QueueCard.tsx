/*
 * 單一 live-OOS 佇列項卡。
 * header：策略 · kind badge · state badge · override 標記。
 * audit：勾選人 + 勾選理由（override 時附 override 理由）—— acceptance「勾選有 audit reason」。
 * 進度：berth 型顯示觀察窗 N/observation_days + 到期倒數（複用 WatchPage 慣例）；replay 完成顯示 run 判決。
 * 連結：Report Viewer · 候選池 · 策略資產三連 —— acceptance「連回 report/candidate/strategy」。
 */
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { LiveOosQueueItem } from '../api/queue'
import {
  isBerthKind,
  kindTone,
  observationPct,
  queueStateTone,
  runIdFromReportRef,
} from './queueDisplay'

export function QueueCard({ item }: { item: LiveOosQueueItem }) {
  const { t } = useTranslation('liveOos')
  const obs = item.observation
  const runId = runIdFromReportRef(item.report_pack_ref)

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      {/* header */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h2 className="text-[18px] font-semibold">{item.strategy}</h2>
        <StatusBadge tone={kindTone(obs.kind)}>
          {t(`queue.kind.${obs.kind}`, { defaultValue: obs.kind })}
        </StatusBadge>
        <StatusBadge tone={queueStateTone(item.state)}>
          {t(`queue.state.${item.state}`, { defaultValue: item.state })}
        </StatusBadge>
        {item.override && (
          <StatusBadge tone="warning">{t('queue.override')}</StatusBadge>
        )}
        {obs.verdict_dsr != null && (
          <span className="ml-auto font-mono text-xs text-text-muted tabular">
            DSR {obs.verdict_dsr.toFixed(4)}
          </span>
        )}
      </div>

      {/* selection audit */}
      <div className="mb-3 rounded-md border border-border/60 bg-surface-raised px-3 py-2 text-xs">
        <div className="text-text-muted">
          {t('queue.selectedBy', { who: item.selected_by, at: item.selected_at.slice(0, 10) })}
        </div>
        {item.selection_reason && (
          <p className="mt-1 text-text-secondary">{item.selection_reason}</p>
        )}
        {item.override && item.override_reason && (
          <p className="mt-1 text-warning">
            {t('queue.overrideReason', { reason: item.override_reason })}
          </p>
        )}
      </div>

      {/* observation progress (berth) or run result (replay) */}
      {isBerthKind(obs.kind) ? (
        <BerthProgress
          observed={obs.observed_trading_days}
          total={obs.observation_days}
          expiry={obs.expiry_date}
          daysRemaining={obs.days_remaining}
        />
      ) : item.run ? (
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-text-muted">{t('queue.runResult')}</span>
          <StatusBadge tone="muted">{item.run.gate_status ?? '—'}</StatusBadge>
          {item.run.run_id && (
            <span className="font-mono tabular text-text-secondary">{item.run.run_id}</span>
          )}
        </div>
      ) : (
        <p className="mb-3 text-xs text-text-muted">{t('queue.replayPending')}</p>
      )}

      {/* three-way links: report / candidate / strategy asset */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border/50 pt-3 text-xs">
        {runId ? (
          <Link to={`/research/reports/${runId}`} className="text-text-secondary underline-offset-2 hover:text-text hover:underline">
            {t('queue.links.report')}
          </Link>
        ) : (
          <span className="text-text-muted">{t('queue.links.reportNa')}</span>
        )}
        <span className="text-text-muted" aria-hidden>·</span>
        <Link to="/research/candidates" className="text-text-secondary underline-offset-2 hover:text-text hover:underline">
          {t('queue.links.candidate')}
        </Link>
        <span className="text-text-muted" aria-hidden>·</span>
        <Link
          to={`/research/strategies/${encodeURIComponent(item.strategy)}`}
          className="text-text-secondary underline-offset-2 hover:text-text hover:underline"
        >
          {t('queue.links.strategy')}
        </Link>
      </div>
    </section>
  )
}

function BerthProgress({
  observed,
  total,
  expiry,
  daysRemaining,
}: {
  observed: number | null
  total: number | null
  expiry: string | null
  daysRemaining: number | null
}) {
  const { t } = useTranslation('liveOos')
  const pct = observationPct(observed, total)
  return (
    <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div>
        <div className="mb-1 flex items-baseline justify-between text-xs text-text-muted">
          <span>{t('queue.observedDays')}</span>
          <span className="font-mono tabular text-text-secondary">
            {observed ?? '—'}/{total ?? '—'}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-raised" role="progressbar" aria-valuenow={pct}>
          <div className="h-full rounded-full bg-gain/70" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <div className="flex flex-col justify-center text-sm">
        {expiry && <div className="text-xs text-text-muted">{t('queue.expiry', { date: expiry })}</div>}
        {daysRemaining != null && (
          <div className="font-mono tabular text-text-secondary">
            {daysRemaining >= 0
              ? t('queue.daysRemaining', { days: daysRemaining })
              : t('queue.overdue', { days: -daysRemaining })}
          </div>
        )}
      </div>
    </div>
  )
}
