/*
 * Run Report（/research/runs/:id）。三源對齊 assembly + design.pen frame + page spec。
 * design.pen sections: header / run_status_banner / kpi_reproduce / tear_sheet / hypothesis_check / next_step_bar。
 * 資料：useRun → GET /runs/{id}（shipped；KPI/reproduce 真實）。tear_sheet（equity 序列）端點未接線 → pending。
 */
import { useNavigate, useParams } from 'react-router-dom'
import { useRun } from '../hooks/useRun'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { Skeleton } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'

// 後端 sim.metrics 真實鍵（four_layer）；百分比欄位以小數傳、前端 ×100（doc 25 §1.3）。
const KPIS: { key: string; label: string; pct?: boolean; signed?: boolean }[] = [
  { key: 'cagr', label: 'CAGR', pct: true, signed: true },
  { key: 'sharpe', label: 'Sharpe' },
  { key: 'maxdd', label: 'MaxDD', pct: true },
  { key: 'win', label: '勝率', pct: true },
  { key: 'trades', label: '交易數' },
  { key: 'slippage_sharpe', label: '滑點 Sharpe' },
]

function KpiCard({ label, value, pct, signed }: { label: string; value: unknown; pct?: boolean; signed?: boolean }) {
  const num = typeof value === 'number' ? value : null
  const tone = signed && num != null ? (num >= 0 ? 'text-gain' : 'text-loss') : 'text-text'
  const arrow = signed && num != null ? (num >= 0 ? '↑ ' : '↓ ') : ''
  const shown =
    num == null
      ? '—'
      : pct
        ? `${arrow}${(num * 100).toFixed(2)}%`
        : `${arrow}${Number.isInteger(num) ? num : num.toFixed(2)}`
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="text-xs text-text-muted">{label}</div>
      <div className={`mt-1 font-mono text-xl tabular ${tone}`}>{shown}</div>
    </div>
  )
}

export function RunReportPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, isError, error, refetch } = useRun(id)
  const run = data?.data

  if (isLoading)
    return (
      <div>
        <PageHeader title="Run Report" route={`/research/runs/${id}`} />
        <Skeleton className="h-32 w-full" />
      </div>
    )

  if (isError || !run)
    return (
      <div>
        <PageHeader title="Run Report" route={`/research/runs/${id}`} />
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">載入失敗：{(error as Error)?.message ?? '找不到此 run'}</p>
          <button
            onClick={() => refetch()}
            className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
          >
            重試
          </button>
        </div>
      </div>
    )

  // RunRecord：run_id 保證，其餘 ledger 欄位 pass-through（index-signature → unknown，需窄化）
  const metrics = (run.metrics ?? {}) as Record<string, unknown>
  const gate = typeof run.gate_status === 'string' ? run.gate_status : '—'
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
      <PageHeader title="Run Report" route={`/research/runs/${run.run_id}`} subtitle={strategy} />

      {/* run_status_banner — IS gate 判定（PASS/FAIL/INCOMPLETE） */}
      <div className="mb-3">
        <StatusBadge tone={gate === 'PASS' ? 'gain' : gate === 'FAIL' ? 'error' : 'warning'}>
          gate: {gate}
        </StatusBadge>
      </div>

      {/* kpi_reproduce */}
      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {KPIS.map((k) => (
          <KpiCard key={k.key} label={k.label} value={metrics[k.key]} pct={k.pct} signed={k.signed} />
        ))}
      </div>
      <div className="mb-3 rounded-lg border border-border bg-surface p-3">
        <div className="mb-1 text-xs text-text-muted">Reproduce</div>
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
        <PendingNote label="Tear sheet（equity / drawdown / rolling Sharpe / heatmap / 分布）" />
      </div>

      {/* next_step_bar */}
      <div className="sticky bottom-0 flex flex-wrap gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm">
        <button
          onClick={() => navigate('/research/runs/new')}
          className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          再迭代
        </button>
        <button
          onClick={() => navigate(`/research/compare?run_ids=${encodeURIComponent(run.run_id)}`)}
          className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          多 run 比較
        </button>
        <button
          onClick={() => navigate(`/research/runs/${encodeURIComponent(run.run_id)}/trades`)}
          className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          逐筆覆盤
        </button>
        <button
          onClick={() => navigate(`/research/validate?run_id=${encodeURIComponent(run.run_id)}`)}
          className="ml-auto rounded-pill bg-text px-4 py-1 font-medium text-base hover:opacity-90 disabled:opacity-50"
          disabled={gate !== 'PASS'}
          title={gate !== 'PASS' ? '需 IS gate PASS 方可送驗證' : undefined}
        >
          送驗證
        </button>
      </div>
    </div>
  )
}
