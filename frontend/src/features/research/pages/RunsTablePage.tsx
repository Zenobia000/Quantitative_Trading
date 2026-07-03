/*
 * Runs Table 研究主頁（/research/runs）。三源對齊：
 * - assembly/research_03_runs_table_integrated.md（結構/行為）
 * - design.pen「Research · Runs Table」frame（header/toolbar/guardrail/runs_table/multi_select/empty）
 * - pages/research_03_runs_table.md（四態/RWD/copy）
 * 資料：useRuns → GET /runs（shipped）。guardrail（trials/DSR）端點未接線 → pending（不假造數字）。
 * RWD：runs_table @<1024 橫向捲動「不轉 card」（研究級密集表）。
 */
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useRuns } from '../hooks/useRuns'
import type { RunRow } from '../api/runs'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'

// 後端 sim.metrics 真實鍵（four_layer）：trades/closed/cagr/sharpe/slippage_sharpe/maxdd/win/…
const METRIC_COLS = ['sharpe', 'cagr', 'maxdd', 'win', 'trades'] as const

function fmtMetric(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(2)
  return v == null ? '—' : String(v)
}

export function RunsTablePage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const [sp, setSp] = useSearchParams()
  // Strategy Library cards drill in with ?strategy_id=… — honour it as a client-side
  // filter over the ledger (the card previously dropped this on the floor).
  const strategyId = sp.get('strategy_id') ?? ''
  const { data, isLoading, isError, error, refetch, isFetching } = useRuns()
  // The ledger is append-only, so the same run_id can appear multiple times
  // (e.g. a DOE re-run). A runs table is one-row-per-run — dedupe by run_id
  // (keep first = newest, ledger is newest-first). Also kills the duplicate
  // React key warning (e2e endpoint-audit F5). Backend ledger hygiene (dropping
  // duplicate appends) is a separate follow-up.
  const rows: RunRow[] = useMemo(() => {
    const seen = new Set<string>()
    const out: RunRow[] = []
    for (const r of data?.data ?? []) {
      if (seen.has(r.run_id)) continue
      seen.add(r.run_id)
      out.push(r)
    }
    return strategyId ? out.filter((r) => r.strategy === strategyId) : out
  }, [data, strategyId])
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const metricCols = useMemo(() => {
    const present = new Set<string>()
    for (const r of rows) for (const m of METRIC_COLS) if (r.metrics?.[m] != null) present.add(m)
    return METRIC_COLS.filter((m) => present.has(m))
  }, [rows])

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  return (
    <div>
      <PageHeader title={t('runs.title')} route="/research/runs" subtitle={t('runs.subtitle')} />

      {/* research_toolbar */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button
          onClick={() => navigate('/research/runs/new')}
          className="rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90"
        >
          {t('runs.newRun')}
        </button>
        <span className="rounded-md border border-border px-2 py-1 text-xs text-text-secondary">
          {t('runs.savedView')}
        </span>
        {strategyId && (
          <span className="inline-flex items-center gap-1.5 rounded-pill border border-border bg-input px-2.5 py-1 text-xs text-text">
            {t('runs.filter.strategyLabel')}
            <span className="font-mono tabular">{strategyId}</span>
            <button
              onClick={() => setSp({})}
              aria-label={t('runs.filter.clearAria')}
              className="text-text-muted hover:text-text"
            >
              ✕
            </button>
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-text-muted tabular">
            {rows.length ? t('runs.showingCount', { n: rows.length }) : ''}
          </span>
          <button
            onClick={() => refetch()}
            className="rounded-md border border-border px-2 py-1 text-xs text-text-secondary hover:text-text"
            disabled={isFetching}
          >
            {isFetching ? t('common:action.refreshing') : t('common:action.refresh')}
          </button>
        </div>
      </div>

      {/* guardrail_bar — trials/DSR/power gauge 端點未接線 */}
      <div className="mb-3">
        <PendingNote label={t('runs.pending.guardrail')} />
      </div>

      {/* runs_table — 四態 */}
      <section className="rounded-lg border border-border bg-surface">
        {isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={8} cols={4 + metricCols.length} />
          </div>
        ) : isError ? (
          <div className="p-6 text-sm">
            <p className="text-error">
              {t('errors:load.failed', { resource: t('runs.resource'), detail: errText(error) })}
            </p>
            <button
              onClick={() => refetch()}
              className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
            >
              {t('common:action.retry')}
            </button>
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8">
            <FirstRunEmptyState
              headline={strategyId ? t('runs.empty.headlineFiltered', { strategyId }) : t('runs.empty.headline')}
              subtitle={t('runs.empty.subtitle')}
              onCta={() => navigate('/research/runs/new')}
            />
          </div>
        ) : (
          // @<1024 橫向捲動保欄位密度（不轉 card）
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-muted">
                  <th className="w-8 p-2"></th>
                  <th className="p-2 font-medium">run_id</th>
                  <th className="p-2 font-medium">{t('runs.table.strategy')}</th>
                  <th className="p-2 font-medium">{t('runs.table.gate')}</th>
                  {metricCols.map((m) => (
                    <th key={m} className="p-2 text-right font-medium">
                      {m}
                    </th>
                  ))}
                  <th className="p-2 font-medium">{t('runs.table.hypothesis')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.run_id}
                    tabIndex={0}
                    onClick={() => navigate(`/research/runs/${encodeURIComponent(r.run_id)}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') navigate(`/research/runs/${encodeURIComponent(r.run_id)}`)
                    }}
                    className="cursor-pointer border-b border-border/60 hover:bg-input focus:bg-input focus:outline-none"
                  >
                    <td className="p-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(r.run_id)}
                        onChange={() => toggle(r.run_id)}
                        aria-label={t('runs.table.selectAria', { runId: r.run_id })}
                      />
                    </td>
                    <td className="p-2 font-mono text-xs tabular">{r.run_id}</td>
                    <td className="p-2 text-text-secondary">{r.strategy ?? '—'}</td>
                    <td className="p-2">
                      <EnumBadge family="gate" value={r.gate_status} />
                    </td>
                    {metricCols.map((m) => (
                      <td key={m} className="p-2 text-right font-mono tabular">
                        {fmtMetric(r.metrics?.[m])}
                      </td>
                    ))}
                    <td className="p-2 max-w-[280px] truncate text-xs text-text-muted" title={r.hypothesis ?? undefined}>
                      {r.hypothesis ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* multi_select_actions */}
      {selected.size > 0 && (
        <div className="sticky bottom-0 mt-3 flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-2 text-sm">
          <span className="text-text-secondary">{t('runs.selected.count', { n: selected.size })}</span>
          <button
            disabled={selected.size < 2}
            onClick={() =>
              navigate(`/research/compare?run_ids=${[...selected].map(encodeURIComponent).join(',')}`)
            }
            className="rounded-md border border-border px-3 py-1 text-text-secondary enabled:hover:text-text disabled:opacity-40"
          >
            {t('runs.selected.compare')}
          </button>
          <button
            onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-text-muted hover:text-text"
          >
            {t('runs.selected.clear')}
          </button>
        </div>
      )}
    </div>
  )
}
