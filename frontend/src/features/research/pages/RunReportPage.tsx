/*
 * Run Report（/research/runs/:id）。三源對齊 assembly + design.pen frame + page spec。
 * design.pen sections: header / run_status_banner / kpi_reproduce / tear_sheet / hypothesis_check / next_step_bar。
 * 資料：useRun → GET /runs/{id}（shipped；KPI/reproduce 真實）。tear_sheet（equity 序列）端點未接線 → pending。
 */
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useRun } from '../hooks/useRun'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { Skeleton } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { StatCard } from '@/components/StatCard'
import { useErrorText } from '@/i18n/useErrorText'

// 後端 sim.metrics 真實鍵（four_layer）；百分比欄位以小數傳、前端 ×100（doc 25 §1.3）。
const KPIS: { key: string; labelKey: string; pct?: boolean; signed?: boolean }[] = [
  { key: 'cagr', labelKey: 'report.kpi.cagr', pct: true, signed: true },
  { key: 'sharpe', labelKey: 'report.kpi.sharpe' },
  { key: 'maxdd', labelKey: 'report.kpi.maxdd', pct: true },
  { key: 'win', labelKey: 'report.kpi.win', pct: true },
  { key: 'trades', labelKey: 'report.kpi.trades' },
  { key: 'slippage_sharpe', labelKey: 'report.kpi.slippageSharpe' },
]

function KpiCard({ label, value, pct, signed }: { label: string; value: unknown; pct?: boolean; signed?: boolean }) {
  return <StatCard label={label} value={typeof value === 'number' ? value : '—'} pct={pct} signed={signed} />
}

export function RunReportPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, isError, error, refetch } = useRun(id)
  const run = data?.data

  if (isLoading)
    return (
      <div>
        <PageHeader title={t('report.title')} route={`/research/runs/${id}`} back={{ label: t('report.back'), to: '/research/runs' }} />
        <Skeleton className="h-32 w-full" />
      </div>
    )

  if (isError || !run)
    return (
      <div>
        <PageHeader title={t('report.title')} route={`/research/runs/${id}`} back={{ label: t('report.back'), to: '/research/runs' }} />
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">
            {t('errors:load.failed', {
              resource: t('report.resource'),
              detail: error ? errText(error) : t('report.notFound'),
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

  // RunRecord：run_id 保證，其餘 ledger 欄位 pass-through（index-signature → unknown，需窄化）
  const metrics = (run.metrics ?? {}) as Record<string, unknown>
  const gateRaw = typeof run.gate_status === 'string' ? run.gate_status : null
  const strategy = typeof run.strategy === 'string' ? run.strategy : undefined
  const runWindow = Array.isArray(run.window) ? (run.window as unknown[]).join(' ~ ') : undefined
  const reproduce: [string, unknown][] = [
    ['run_id', run.run_id],
    ['strategy', strategy],
    ['engine', run['engine']],
    ['window', runWindow],
    ['created_at', run['created_at']],
  ]

  return (
    <div>
      <PageHeader title={t('report.title')} route={`/research/runs/${run.run_id}`} subtitle={strategy} back={{ label: t('report.back'), to: '/research/runs' }} />

      {/* run_status_banner — IS gate 判定（PASS/FAIL/INCOMPLETE） */}
      <div className="mb-3 flex items-center gap-2">
        <span className="text-xs text-text-muted">{t('report.gateLabel')}</span>
        <EnumBadge family="gate" value={gateRaw} />
      </div>

      {/* kpi_reproduce */}
      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {KPIS.map((k) => (
          <KpiCard key={k.key} label={t(k.labelKey)} value={metrics[k.key]} pct={k.pct} signed={k.signed} />
        ))}
      </div>
      <div className="mb-3 rounded-lg border border-border bg-surface p-3">
        <div className="mb-1 text-xs text-text-muted">{t('report.reproduce')}</div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-xs">
          {reproduce.map(([k, v]) => (
            <span key={k} className="text-text-secondary">
              {k}: <span className="text-text">{v == null ? '—' : String(v)}</span>
            </span>
          ))}
        </div>
      </div>

      {/* tear_sheet — equity/drawdown 序列端點未接線 */}
      <div className="mb-3">
        <PendingNote label={t('report.pending.tearSheet')} />
      </div>

      {/* next_step_bar */}
      <div className="sticky bottom-0 flex flex-wrap gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm">
        <button
          onClick={() => navigate('/research/runs/new')}
          className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          {t('report.action.iterate')}
        </button>
        <button
          onClick={() => navigate(`/research/compare?run_ids=${encodeURIComponent(run.run_id)}`)}
          className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          {t('report.action.compare')}
        </button>
        <button
          onClick={() => navigate(`/research/runs/${encodeURIComponent(run.run_id)}/trades`)}
          className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          {t('report.action.tradeReview')}
        </button>
        <button
          onClick={() => navigate(`/research/validate?run_id=${encodeURIComponent(run.run_id)}`)}
          className="ml-auto rounded-pill bg-text px-4 py-1 font-medium text-base hover:opacity-90 disabled:opacity-50"
          disabled={gateRaw !== 'PASS'}
          title={gateRaw !== 'PASS' ? t('report.action.validateHint') : undefined}
        >
          {t('report.action.validate')}
        </button>
      </div>
    </div>
  )
}
