/*
 * 策略庫（/research/strategies）。三源對齊 assembly + design.pen frame + page spec。
 * strategy_list 接真實 GET /research/strategies（runs ledger projection）；四態完備。
 * version_timeline（版本沿革 + 假設 diff）需 /research/strategies/{id}/versions（needs-work）→ pending。
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useStrategies } from '../hooks/useStrategies'
import type { StrategyRow } from '../api/strategies'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'

function fmt(v: unknown): string {
  return typeof v === 'number' ? (Number.isInteger(v) ? String(v) : v.toFixed(2)) : '—'
}

export function StrategyLibraryPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const { data, isLoading, isError, error, refetch } = useStrategies()
  const rows: StrategyRow[] = data?.data ?? []

  return (
    <div>
      <PageHeader title={t('strategies.title')} route="/research/strategies" subtitle={t('strategies.subtitle')} />

      {/* toolbar */}
      <div className="mb-3 flex items-center gap-2">
        <button
          onClick={() => navigate('/research/runs/new?new_strategy=1')}
          className="rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90"
        >
          {t('strategies.newStrategy')}
        </button>
        {rows.length > 0 && (
          <span className="ml-auto text-xs text-text-muted tabular">{t('strategies.count', { n: rows.length })}</span>
        )}
      </div>

      {/* strategy_list — 四態 */}
      {isLoading ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <SkeletonRows rows={3} cols={4} />
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">
            {t('errors:load.failed', { resource: t('strategies.resource'), detail: errText(error) })}
          </p>
          <button onClick={() => refetch()} className="mt-3 rounded-md border border-border px-3 py-1.5 hover:text-text">
            {t('common:action.retry')}
          </button>
        </div>
      ) : rows.length === 0 ? (
        <FirstRunEmptyState onCta={() => navigate('/research/runs/new')} />
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((s) => {
            const gatePassed = s.validation_status === 'is_pass'
            return (
              <div
                key={s.strategy_id}
                className="flex flex-col rounded-lg border border-border bg-surface hover:border-text/40"
              >
                {/* 主點擊區：帶策略篩選進 Runs Table（篩選現已被 Runs 端接住） */}
                <button
                  onClick={() => navigate(`/research/runs?strategy_id=${encodeURIComponent(s.strategy_id)}`)}
                  className="p-4 text-left"
                >
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold">{s.strategy_id}</h3>
                    <span className="font-mono text-xs text-text-muted">{s.version}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <EnumBadge family="validation" value={s.validation_status} />
                    <EnumBadge family="stage" value={s.stage} />
                    <span className="ml-auto text-xs text-text-muted tabular">
                      {t('strategies.card.runsCount', { n: s.runs_count })}
                    </span>
                  </div>
                  <div className="mt-3 flex gap-4 font-mono text-xs text-text-secondary tabular">
                    <span>Sharpe {fmt((s.best_kpi as Record<string, unknown>)?.sharpe)}</span>
                    <span>CAGR {fmt((s.best_kpi as Record<string, unknown>)?.cagr)}</span>
                  </div>
                </button>
                {/* footer：研究迴圈的下一步 —— 通過驗證閘者才解鎖「晉升」（gated forward edge） */}
                <div className="flex items-center gap-3 border-t border-border/60 px-4 py-2 text-xs">
                  <button
                    onClick={() => navigate(`/research/runs?strategy_id=${encodeURIComponent(s.strategy_id)}`)}
                    className="text-text-secondary hover:text-text"
                  >
                    {t('strategies.card.viewRuns')}
                  </button>
                  {gatePassed ? (
                    <button
                      onClick={() => navigate(`/research/promote/${encodeURIComponent(s.strategy_id)}`)}
                      className="ml-auto font-medium text-text hover:opacity-80"
                    >
                      {t('strategies.card.promote')}
                    </button>
                  ) : (
                    <span className="ml-auto text-text-muted" title={t('strategies.card.promoteLockedHint')}>
                      {t('strategies.card.promoteLocked')}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* version_timeline — 版本沿革端點 needs-work */}
      <div className="mt-3">
        <PendingNote label={t('strategies.pending.versionTimeline')} />
      </div>
    </div>
  )
}
