/*
 * Run Report v1（/research/runs/:id）—— FinLab 對標 P0 核心：觀察艙三個月的日常介面。
 * 由上而下：判決卡（gate + criteria 燈號 + DSR 標尺）→ KPI / reproduce → 分段 equity+drawdown
 * → 月報酬熱圖 → 回撤事件表 → 成本敏感 → Open-in-notebook → next-step bar。
 * 三資料源：useRun（KPI/reproduce/gate/window）+ useRunReport（verdict/segments/monthly/dd/cost）
 * + useRunEquity（曲線序列）。所有 report 欄位可 null（null=誠實無資料，GOAL #8）。
 */
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useRun } from '../hooks/useRun'
import { useRunReport } from '../hooks/useRunReport'
import { useRunEquity } from '../hooks/useRunSeries'
import { VerdictCard } from '../components/VerdictCard'
import { ReportEquityChart } from '../components/ReportEquityChart'
import { MonthlyHeatmap } from '../components/MonthlyHeatmap'
import { DrawdownEventsTable } from '../components/DrawdownEventsTable'
import { NotebookButton } from '../components/NotebookButton'
import { PageHeader } from '@/components/PageHeader'
import { Skeleton, SkeletonRows } from '@/components/Skeleton'
import { useErrorText } from '@/i18n/useErrorText'

// 後端 sim.metrics 真實鍵（four_layer）；百分比欄以小數傳、前端 ×100（doc 25 §1.3）。
const KPIS: { key: string; labelKey: string; pct?: boolean; signed?: boolean }[] = [
  { key: 'cagr', labelKey: 'report.kpi.cagr', pct: true, signed: true },
  { key: 'sharpe', labelKey: 'report.kpi.sharpe' },
  { key: 'maxdd', labelKey: 'report.kpi.maxdd', pct: true },
  { key: 'win', labelKey: 'report.kpi.win', pct: true },
  { key: 'trades', labelKey: 'report.kpi.trades' },
  { key: 'slippage_sharpe', labelKey: 'report.kpi.slippageSharpe' },
]

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

function fmtEvidence(v: number | string | null, pct?: boolean): string {
  if (v == null) return '—'
  if (typeof v === 'string') return v
  if (pct) return `${(v * 100).toFixed(2)}%`
  return Number.isInteger(v) ? String(v) : v.toFixed(2)
}

function EvidenceCell({
  label,
  value,
  pct,
  signed,
  hint,
}: {
  label: string
  value: number | string | null
  pct?: boolean
  signed?: boolean
  hint?: string
}) {
  const numValue = typeof value === 'number' ? value : null
  const tone = signed && numValue != null ? (numValue >= 0 ? 'text-gain' : 'text-loss') : 'text-text'
  return (
    <div className="border border-border bg-base px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.14em] text-text-muted">{label}</div>
      <div className={`mt-1 font-mono text-[15px] tabular ${tone}`}>{fmtEvidence(value, pct)}</div>
      {hint && <div className="mt-1 text-[11px] text-text-muted">{hint}</div>}
    </div>
  )
}

export function RunReportPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, isError, error, refetch } = useRun(id)
  const reportQ = useRunReport(id)
  const equityQ = useRunEquity(id)
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
        <div className="border border-border bg-panel p-6 text-sm">
          <p className="text-error">
            {t('errors:load.failed', {
              resource: t('report.resource'),
              detail: error ? errText(error) : t('report.notFound'),
            })}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-3 border border-border px-3 py-1.5 text-text-secondary hover:border-border-strong hover:text-text"
          >
            {t('common:action.retry')}
          </button>
        </div>
      </div>
    )

  // RunRecord：run_id 保證，其餘 ledger 欄位 pass-through（index-signature → unknown，需窄化）。
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

  const report = reportQ.data?.data
  const segments = report?.segments
  const cost = report?.cost_sensitivity
  const costSharpe = num(cost?.sharpe)
  const costSlip = num(cost?.slippage_sharpe)
  const costDiff = costSharpe != null && costSlip != null ? costSlip - costSharpe : null

  const equity = equityQ.data?.data?.equity ?? []
  const drawdown = equityQ.data?.data?.drawdown ?? []
  const isStart = segments?.run_window?.is_start ?? null
  const oosStart = segments?.truth_gate_window?.oos_start ?? null

  return (
    <div>
      <PageHeader title={t('report.title')} route={`/research/runs/${run.run_id}`} subtitle={strategy} back={{ label: t('report.back'), to: '/research/runs' }} />

      <div className="mb-3 border border-border bg-panel">
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-text-muted">Run Evidence Ledger</div>
            <div className="mt-0.5 text-xs text-text-secondary">{strategy ?? '—'}</div>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2 font-mono text-[11px] uppercase tracking-[0.08em]">
            <span className="border border-info/50 px-2 py-1 text-info">RUN {run.run_id}</span>
            <span className="border border-border px-2 py-1 text-text-secondary">GATE {gateRaw ?? '—'}</span>
            <span className="border border-border px-2 py-1 text-text-muted">OOS {oosStart ?? '—'}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 px-3 py-2 font-mono text-xs">
          {reproduce.map(([k, v]) => (
            <span key={k} className="text-text-secondary">
              {k}: <span className="text-text">{v == null ? '—' : String(v)}</span>
            </span>
          ))}
        </div>
      </div>

      {/* 判決卡（置頂，本平台差異化） */}
      <VerdictCard verdict={report?.verdict} gateStatusFallback={gateRaw} metrics={metrics} />

      {/* kpi_reproduce */}
      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {KPIS.map((k) => (
          <EvidenceCell
            key={k.key}
            label={t(k.labelKey)}
            value={num(metrics[k.key])}
            pct={k.pct}
            signed={k.signed}
          />
        ))}
      </div>

      {/* 分段 equity + drawdown */}
      <section className="mb-3 border border-border bg-panel p-4">
        <div className="mb-2 flex flex-wrap items-baseline gap-2">
          <h2 className="text-[18px] font-semibold">{t('report.equity.title')}</h2>
          {oosStart && (
            <span className="text-[11px] text-text-muted">{t('report.equity.sealedBoundary', { date: oosStart })}</span>
          )}
        </div>
        {equityQ.isLoading ? (
          <SkeletonRows rows={5} cols={1} />
        ) : equity.length === 0 ? (
          <p className="rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-sm text-text-muted">
            {t('report.equity.empty')}
          </p>
        ) : (
          <>
            <ReportEquityChart equity={equity} drawdown={drawdown} isStart={isStart} oosStart={oosStart} />
            {isStart && <p className="mt-1 text-[11px] text-text-muted">{t('report.equity.basisHint')}</p>}
          </>
        )}
      </section>

      {/* 月報酬熱圖 */}
      <MonthlyHeatmap monthly={report?.monthly_returns} note={report?.monthly_returns_note} />

      {/* 回撤事件表 */}
      <DrawdownEventsTable events={report?.drawdown_events} />

      {/* 成本敏感 */}
      <section className="mb-3 border border-border bg-panel p-4">
        <h2 className="mb-2 text-[18px] font-semibold">{t('report.cost.title')}</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <EvidenceCell label={t('report.cost.sharpe')} value={costSharpe} />
          <EvidenceCell label={t('report.cost.slippageSharpe')} value={costSlip} />
          <EvidenceCell label={t('report.cost.diff')} value={costDiff} signed hint={t('report.cost.hint')} />
        </div>
      </section>

      {/* Open-in-notebook + 完整報告（Goal 5 Report Viewer）。
          帶 run_id：Report Viewer 的 getEvaluation 會以候選池 report_pack_ref 反查出對應
          evaluation_id（store 以 evaluation_id 為鍵）；反查不到 → 404 → fixture fallback。 */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <NotebookButton runId={run.run_id} />
        <button
          onClick={() => navigate(`/research/reports/${encodeURIComponent(run.run_id)}`)}
          className="inline-flex items-center gap-1.5 border border-border px-3 py-1.5 text-sm text-text-secondary hover:border-border-strong hover:text-text"
        >
          <span aria-hidden>↗</span>
          {t('report.action.fullReport')}
        </button>
      </div>

      {/* next_step_bar */}
      <div className="sticky bottom-0 flex flex-wrap gap-2 border border-border bg-panel px-4 py-2 text-sm">
        <button
          onClick={() => navigate('/research/runs/new')}
          className="border border-border px-3 py-1 font-mono text-xs uppercase tracking-[0.08em] text-text-secondary hover:border-border-strong hover:text-text"
        >
          {t('report.action.iterate')}
        </button>
        <button
          onClick={() => navigate(`/research/compare?run_ids=${encodeURIComponent(run.run_id)}`)}
          className="border border-border px-3 py-1 font-mono text-xs uppercase tracking-[0.08em] text-text-secondary hover:border-border-strong hover:text-text"
        >
          {t('report.action.compare')}
        </button>
        <button
          onClick={() => navigate(`/research/runs/${encodeURIComponent(run.run_id)}/trades`)}
          className="border border-border px-3 py-1 font-mono text-xs uppercase tracking-[0.08em] text-text-secondary hover:border-border-strong hover:text-text"
        >
          {t('report.action.tradeReview')}
        </button>
        <button
          onClick={() => navigate(`/deploy/gate?run_id=${encodeURIComponent(run.run_id)}`)}
          className="ml-auto border border-info/60 bg-input px-4 py-1 font-mono text-xs font-semibold uppercase tracking-[0.08em] text-text hover:border-info disabled:opacity-50"
          disabled={gateRaw !== 'PASS'}
          title={gateRaw !== 'PASS' ? t('report.action.validateHint') : undefined}
        >
          {t('report.action.validate')}
        </button>
      </div>
    </div>
  )
}
