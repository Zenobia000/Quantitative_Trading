/*
 * 策略資產 · 清單（/research/strategies）—— 以「策略」為軸的研究資產工作台（Goal 7）。
 * 每卡：策略名 + title、一行假設（候選 → 最近 run → 型錄機制 fallback）、候選狀態 badge、
 * 五維 scorecard 迷你燈、最近判決 gate badge、觀察艙 badge、profile/label、run 數，
 * 加主要動作「Evaluate」CTA（導向 /research/runs/new?strategy= —— 目前 evaluate 後端僅 CLI）。
 * 點資訊區 → 詳情（/research/strategies/:name）。archived / 無 run 策略仍由型錄可發現。
 * 資料聚合全用既有端點（/strategies + /runs + /monitor/watch + /research/candidates），不需新後端。
 * 四態由型錄（roster 主源）驅動；runs/watch/candidate 為 enrichment，缺席不阻塞清單。
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useStrategyHubList, type StrategyHubRow } from '../hooks/useStrategyHub'
import { CandidateStateBadge } from '../components/candidates/CandidateStateBadge'
import { ScorecardLights } from '../components/candidates/ScorecardLights'
import { PageHeader } from '@/components/PageHeader'
import { SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'

/** Evaluate 入口：evaluate 後端目前僅 CLI，前端先導既有 New Run 表單（IA §2：runs/new 併入 evaluate）。 */
function evaluateHref(name: string): string {
  return `/research/runs/new?strategy=${encodeURIComponent(name)}`
}

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
            <StrategyAssetCard
              key={s.name}
              row={s}
              onOpen={() => navigate(`/research/strategies/${encodeURIComponent(s.name)}`)}
              onEvaluate={() => navigate(evaluateHref(s.name))}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/** 單一策略資產卡：info 區可點進詳情；Evaluate 為分離的主要動作（避免巢狀 button）。 */
function StrategyAssetCard({
  row,
  onOpen,
  onEvaluate,
}: {
  row: StrategyHubRow
  onOpen: () => void
  onEvaluate: () => void
}) {
  const { t } = useTranslation('research')
  return (
    <div className="flex flex-col rounded-lg border border-border bg-surface p-4">
      {/* info 區（可點進詳情） */}
      <button onClick={onOpen} className="flex flex-col text-left">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold">{row.title}</h3>
          <span className="font-mono text-xs text-text-muted">{row.name}</span>
        </div>

        {/* 一行假設（候選 → 最近 run → 型錄機制 fallback） */}
        {row.hypothesis && (
          <p className="mt-1 truncate text-xs text-text-secondary" title={row.hypothesis}>
            {row.hypothesis}
          </p>
        )}

        {/* 狀態列：候選 state + 最近判決 gate + 觀察艙 */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {row.candidate && <CandidateStateBadge state={row.candidate.state} />}
          {row.latestRun ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="text-xs text-text-muted">{t('strategyHub.list.card.latestGate')}</span>
              <EnumBadge family="gate" value={row.latestGateStatus} />
            </span>
          ) : (
            <span className="text-xs text-text-muted">{t('strategyHub.list.card.noRuns')}</span>
          )}
          {row.watch && <EnumBadge family="watchState" value={row.watch.status} />}
        </div>

        {/* 五維 scorecard 迷你燈（有候選才顯示） */}
        {row.candidate && (
          <div className="mt-2">
            <ScorecardLights summary={row.candidate.scorecard_summary} />
          </div>
        )}

        {/* profile / label + run 數 */}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          {row.candidate ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="text-text-muted">{t('strategyHub.list.card.profile')}</span>
              <span className="font-mono text-text-secondary">{row.candidate.latest_profile}</span>
              <span className="text-text-muted" aria-hidden>·</span>
              <span className="text-text-secondary">{row.candidate.latest_label}</span>
            </span>
          ) : (
            <span className="text-text-muted">{t('strategyHub.list.card.notEvaluated')}</span>
          )}
          <span className="ml-auto text-text-muted tabular">
            {t('strategyHub.list.card.runs', { n: row.runsCount })}
          </span>
        </div>
      </button>

      {/* 主要動作：Evaluate（分離於 info 區之外，非巢狀 button） */}
      <div className="mt-3 border-t border-border/50 pt-3">
        <button
          onClick={onEvaluate}
          className="w-full rounded-md border border-text/40 px-3 py-1.5 text-xs font-medium text-text hover:bg-input"
        >
          {t('strategyHub.list.evaluate')}
        </button>
      </div>
    </div>
  )
}
