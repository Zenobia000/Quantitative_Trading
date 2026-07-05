/*
 * Report Viewer（/research/reports/:runId）—— rebuild Goal 5：取代舊 Run Report 為 FinLab 對標
 * 研究報告工作台。由上而下：headline banner（首屏三答）→ 五張 scorecard 摘要 → sheet tabs（維度明細）
 * → evidence/gate checks（DsrRuler + hard-fail 燈）→ linked trade log → decision action bar。
 *
 * 資料源 fixture-first（getEvaluation：先真 API，後端 Goal 3/4 未落地 fallback bundled fixture），
 * UI 以 DataSourceBadge 明示真 API vs fixture。契約真相源 dev_docs/contracts/evaluation_result.example.json。
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { Skeleton } from '@/components/Skeleton'
import { useErrorText } from '@/i18n/useErrorText'
import { useEvaluation } from '../hooks/useEvaluation'
import { ReportHeadlineBanner } from '../components/reportviewer/ReportHeadlineBanner'
import { ScorecardGrid } from '../components/reportviewer/ScorecardGrid'
import { ScorecardTabs } from '../components/reportviewer/ScorecardTabs'
import { GateChecksSection } from '../components/reportviewer/GateChecksSection'
import { LinkedTradeLogSection } from '../components/reportviewer/LinkedTradeLogSection'
import { SimulationPanel } from '../components/reportviewer/SimulationPanel'
import { DecisionActionBar } from '../components/reportviewer/DecisionActionBar'
import { DataSourceBadge } from '../components/reportviewer/DataSourceBadge'

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

export function ReportViewerPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const { runId } = useParams<{ runId: string }>()
  const { data: load, isLoading, isError, error, refetch } = useEvaluation(runId)
  // sheet tab / scorecard 選中維度（預設第一張，通常 profitability）。
  const [active, setActive] = useState<string>('profitability')

  const back = { label: t('reportViewer.back'), to: '/research/runs' }

  if (isLoading)
    return (
      <div>
        <PageHeader title={t('reportViewer.title')} route={`/research/reports/${runId ?? ''}`} back={back} />
        <Skeleton className="h-40 w-full" />
      </div>
    )

  if (isError || !load)
    return (
      <div>
        <PageHeader title={t('reportViewer.title')} route={`/research/reports/${runId ?? ''}`} back={back} />
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">
            {t('errors:load.failed', {
              resource: t('reportViewer.resource'),
              detail: error ? errText(error) : t('reportViewer.notFound'),
            })}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
          >
            {t('common:action.retry')}
          </button>
        </div>
      </div>
    )

  const result = load.data
  const activeCategory = result.scorecards.some((sc) => sc.category === active)
    ? active
    : (result.scorecards[0]?.category ?? 'profitability')

  // Win-Rate 整張 not_available（panel 無 per-trade pnl）→ 連結逐筆覆盤標 partial（僅再平衡列）。
  const winRate = result.scorecards.find((sc) => sc.category === 'win_rate')
  const tradesPartial = winRate?.status === 'not_available'

  return (
    <div>
      <PageHeader
        title={t('reportViewer.title')}
        route={`/research/reports/${result.run_id}`}
        subtitle={result.strategy}
        back={back}
      />

      <div className="mb-3 border border-border bg-panel">
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-text-muted">Evaluation Evidence Ledger</div>
            <div className="mt-0.5 text-xs text-text-secondary">{result.strategy}</div>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2 font-mono text-[11px] uppercase tracking-[0.08em]">
            <span className="border border-info/50 px-2 py-1 text-info">RUN {result.run_id}</span>
            <span className="border border-border px-2 py-1 text-text-secondary">EVAL {result.evaluation_id}</span>
            <span className="border border-border px-2 py-1 text-text-muted">PROFILE {result.profile}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 px-3 py-2">
          <DataSourceBadge source={load.source} />
          <span className="font-mono text-xs text-text-muted">created_at {result.created_at}</span>
        </div>
      </div>

      <ReportHeadlineBanner result={result} />

      <ScorecardGrid scorecards={result.scorecards} activeCategory={activeCategory} onSelect={setActive} />

      <ScorecardTabs
        scorecards={result.scorecards}
        runId={result.run_id}
        activeCategory={activeCategory}
        onSelect={setActive}
      />

      <GateChecksSection
        checks={result.checks}
        dsr={num(result.headline_metrics.dsr)}
        truthVerdict={result.verdict.truth_verdict ?? ''}
      />

      <LinkedTradeLogSection runId={result.run_id} partial={tradesPartial} />

      <SimulationPanel
        runId={result.run_id}
        source={load.source}
        evaluationId={result.evaluation_id}
        strategy={result.strategy}
      />

      <DecisionActionBar
        source={load.source}
        recommendationAction={result.verdict.recommendation.action}
        strategy={result.strategy}
        recommendation={result.verdict.live_oos_recommendation}
      />
    </div>
  )
}
