/*
 * 策略資產 · 清單（/research/strategies）—— strategy ledger。
 * 以「策略」為軸聚合 roster / runs / watch / candidates，輸出可掃描的研究資產帳本：
 * identity / hypothesis / evidence / governance state / action。無 run、archived、未評估策略仍保留。
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

function fmtMetric(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(2)
  return v == null ? '—' : String(v)
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

      <div className="mb-3 flex items-center gap-2 border border-border bg-panel px-3 py-2">
        <button
          onClick={() => navigate('/research/runs/new')}
          className="border border-info/60 bg-input px-3 py-1.5 font-mono text-xs font-semibold uppercase tracking-[0.08em] text-text hover:border-info"
        >
          {t('strategyHub.list.newRun')}
        </button>
        {rows.length > 0 && (
          <span className="ml-auto font-mono text-xs text-text-muted tabular">
            {t('strategyHub.list.count', { n: rows.length })}
          </span>
        )}
      </div>

      {/* roster — 四態（型錄驅動） */}
      {registry.isLoading ? (
        <div className="border border-border bg-panel p-4">
          <SkeletonRows rows={3} cols={4} />
        </div>
      ) : registry.isError ? (
        <div className="border border-border bg-panel p-6 text-sm">
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
        <div className="overflow-x-auto border border-border bg-panel">
          <div className="min-w-[1100px] border-b border-border bg-base px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted lg:grid lg:grid-cols-[minmax(260px,1.3fr)_minmax(250px,1.2fr)_220px_190px_170px] lg:gap-3">
            <span>Strategy</span>
            <span>Hypothesis / Mechanism</span>
            <span>Evidence</span>
            <span>Governance</span>
            <span>Controls</span>
          </div>
          <div>
            {rows.map((s) => (
              <StrategyAssetRow
                key={s.name}
                row={s}
                onOpen={() => navigate(`/research/strategies/${encodeURIComponent(s.name)}`)}
                onEvaluate={() => navigate(evaluateHref(s.name))}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StrategyAssetRow({
  row,
  onOpen,
  onEvaluate,
}: {
  row: StrategyHubRow
  onOpen: () => void
  onEvaluate: () => void
}) {
  const { t } = useTranslation('research')
  const latestSharpe = row.latestRun?.metrics?.sharpe
  const latestDsr = row.latestRun?.metrics?.dsr
  const latestMaxdd = row.latestRun?.metrics?.maxdd

  return (
    <section className="min-w-[1100px] border-b border-border bg-surface px-3 py-3 last:border-b-0 hover:bg-row lg:grid lg:grid-cols-[minmax(260px,1.3fr)_minmax(250px,1.2fr)_220px_190px_170px] lg:gap-3">
      <button onClick={onOpen} className="min-w-0 text-left">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-[13px] font-semibold text-text">{row.title}</h3>
          <span className="font-mono text-xs text-text-muted">{row.name}</span>
          {row.candidate && <CandidateStateBadge state={row.candidate.state} />}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
          {row.latestRun ? (
            <>
              <span className="text-text-muted">{t('strategyHub.list.card.latestGate')}</span>
              <EnumBadge family="gate" value={row.latestGateStatus} />
            </>
          ) : (
            <span className="text-text-muted">{t('strategyHub.list.card.noRuns')}</span>
          )}
          {row.watch && <EnumBadge family="watchState" value={row.watch.status} />}
        </div>
      </button>

      <button onClick={onOpen} className="mt-3 min-w-0 text-left lg:mt-0">
        {row.hypothesis && (
          <p className="truncate text-xs text-text-secondary" title={row.hypothesis}>
            {row.hypothesis}
          </p>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
          {row.candidate ? (
            <>
              <span className="text-text-muted">{t('strategyHub.list.card.profile')}</span>
              <span className="font-mono text-text-secondary">{row.candidate.latest_profile}</span>
              <span className="text-text-muted" aria-hidden>·</span>
              <span className="text-text-secondary">{row.candidate.latest_label}</span>
            </>
          ) : (
            <span className="text-text-muted">{t('strategyHub.list.card.notEvaluated')}</span>
          )}
        </div>
      </button>

      <div className="mt-3 lg:mt-0">
        <div className="grid grid-cols-3 gap-2">
          <EvidenceCell label="sharpe" value={fmtMetric(latestSharpe)} />
          <EvidenceCell label="dsr" value={fmtMetric(latestDsr)} />
          <EvidenceCell label="maxdd" value={fmtMetric(latestMaxdd)} />
        </div>
        {row.candidate && (
          <div className="mt-2">
            <ScorecardLights summary={row.candidate.scorecard_summary} />
          </div>
        )}
      </div>

      <div className="mt-3 lg:mt-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] uppercase tracking-[0.12em] text-text-muted">runs</span>
          <span className="font-mono text-xs text-text-secondary tabular">
            {t('strategyHub.list.card.runs', { n: row.runsCount })}
          </span>
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-[11px] uppercase tracking-[0.12em] text-text-muted">watch</span>
          <span className="font-mono text-xs text-text-secondary tabular">
            {row.watch?.observed_trading_days ?? '—'}/{row.watch?.nominal_trading_days ?? '—'}
          </span>
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-2 lg:mt-0">
        <button
          onClick={onEvaluate}
          className="border border-info/60 bg-input px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-text hover:border-info"
        >
          {t('strategyHub.list.evaluate')}
        </button>
        <button
          onClick={onOpen}
          className="border border-border px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.08em] text-text-secondary hover:border-border-strong hover:text-text"
        >
          Open
        </button>
      </div>
    </section>
  )
}

function EvidenceCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border bg-base px-2 py-1">
      <div className="text-[9px] uppercase tracking-[0.12em] text-text-muted">{label}</div>
      <div className="font-mono text-[12px] text-text-secondary tabular">{value}</div>
    </div>
  )
}
