/*
 * 策略中心 · 清單（/research/strategies）—— 退役 StrategyLibraryPage，改以「策略」為軸。
 * 每卡：策略名 + title、準則摘要（型錄 description）、最近一次 run 的 gate badge、
 * 觀察艙狀態 badge（在艙才顯示）、run 數。點卡 → 詳情（/research/strategies/:name）。
 * 資料聚合全用既有端點（/strategies + /runs + /monitor/watch），不需新後端。
 * 四態由型錄（roster 主源）驅動；runs/watch 為 enrichment，缺席不阻塞清單。
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useStrategyHubList } from '../hooks/useStrategyHub'
import { PageHeader } from '@/components/PageHeader'
import { SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'

export function StrategyHubListPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const { registry, rows } = useStrategyHubList()

  return (
    <div>
      <PageHeader
        title={t('strategyHub.list.title')}
        route="/research/strategies"
        subtitle={t('strategyHub.list.subtitle')}
      />

      {/* toolbar */}
      <div className="mb-3 flex items-center gap-2">
        <button
          onClick={() => navigate('/research/runs/new')}
          className="rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90"
        >
          {t('strategyHub.list.newRun')}
        </button>
        {rows.length > 0 && (
          <span className="ml-auto text-xs text-text-muted tabular">
            {t('strategyHub.list.count', { n: rows.length })}
          </span>
        )}
      </div>

      {/* roster — 四態（型錄驅動） */}
      {registry.isLoading ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <SkeletonRows rows={3} cols={4} />
        </div>
      ) : registry.isError ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">
            {t('errors:load.failed', { resource: t('strategyHub.list.resource'), detail: errText(registry.error) })}
          </p>
          <button
            onClick={() => registry.refetch()}
            className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
          >
            {t('common:action.retry')}
          </button>
        </div>
      ) : rows.length === 0 ? (
        <FirstRunEmptyState onCta={() => navigate('/research/runs/new')} />
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((s) => (
            <button
              key={s.name}
              onClick={() => navigate(`/research/strategies/${encodeURIComponent(s.name)}`)}
              className="flex flex-col rounded-lg border border-border bg-surface p-4 text-left hover:border-text/40"
            >
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold">{s.title}</h3>
                <span className="font-mono text-xs text-text-muted">{s.name}</span>
              </div>
              {s.description && (
                <p className="mt-1 truncate text-xs text-text-secondary" title={s.description}>
                  {s.description}
                </p>
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {s.latestRun ? (
                  <span className="inline-flex items-center gap-1.5">
                    <span className="text-xs text-text-muted">{t('strategyHub.list.card.latestGate')}</span>
                    <EnumBadge family="gate" value={s.latestGateStatus} />
                  </span>
                ) : (
                  <span className="text-xs text-text-muted">{t('strategyHub.list.card.noRuns')}</span>
                )}
                {s.watch && <EnumBadge family="watchState" value={s.watch.status} />}
                <span className="ml-auto text-xs text-text-muted tabular">
                  {t('strategyHub.list.card.runs', { n: s.runsCount })}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
