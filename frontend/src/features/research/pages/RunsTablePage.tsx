/*
 * Runs ledger（/research/runs）。
 * 資料：useRuns → GET /runs（shipped）。guardrail（trials/DSR）端點未接線 → pending（不假造數字）。
 * RWD：@<1024 橫向捲動「不轉 card」（研究級密集表）。
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

function gateCounts(rows: RunRow[]): { pass: number; fail: number; other: number } {
  let pass = 0
  let fail = 0
  let other = 0
  for (const row of rows) {
    const gate = String(row.gate_status ?? '').toUpperCase()
    if (gate === 'PASS') pass += 1
    else if (gate === 'FAIL') fail += 1
    else other += 1
  }
  return { pass, fail, other }
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
  const gates = useMemo(() => gateCounts(rows), [rows])

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  return (
    <div>
      <PageHeader title={t('runs.title')} route="/research/runs" subtitle={t('runs.subtitle')} />

      <div className="mb-3 border border-border bg-panel">
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-text-muted">Run Ledger</div>
            <div className="mt-0.5 text-xs text-text-secondary">{t('runs.savedView')}</div>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2 font-mono text-[11px] uppercase tracking-[0.08em]">
            <span className="border border-border px-2 py-1 text-text-secondary">
              {rows.length ? t('runs.showingCount', { n: rows.length }) : '0'}
            </span>
            <span className="border border-gain/40 px-2 py-1 text-gain">PASS {gates.pass}</span>
            <span className="border border-loss/40 px-2 py-1 text-loss">FAIL {gates.fail}</span>
            <span className="border border-border px-2 py-1 text-text-muted">OTHER {gates.other}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 px-3 py-2">
          <button
            onClick={() => navigate('/research/runs/new')}
            className="border border-info/60 bg-input px-3 py-1.5 font-mono text-xs font-semibold uppercase tracking-[0.08em] text-text hover:border-info"
          >
            {t('runs.newRun')}
          </button>
          {strategyId && (
            <span className="inline-flex items-center gap-1.5 border border-border bg-input px-2.5 py-1 font-mono text-xs text-text">
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
            <button
              onClick={() => refetch()}
              className="border border-border px-2 py-1 font-mono text-xs uppercase tracking-[0.08em] text-text-secondary hover:border-border-strong hover:text-text"
              disabled={isFetching}
            >
              {isFetching ? t('common:action.refreshing') : t('common:action.refresh')}
            </button>
          </div>
        </div>
      </div>

      {/* guardrail_bar — trials/DSR/power gauge 端點未接線 */}
      <div className="mb-3">
        <PendingNote label={t('runs.pending.guardrail')} />
      </div>

      {/* runs_table — 四態 */}
      <section className="border border-border bg-panel">
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
              className="mt-3 border border-border px-3 py-1.5 text-text-secondary hover:border-border-strong hover:text-text"
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
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-sm">
              <thead>
                <tr className="border-b border-border bg-base text-left font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                  <th className="w-8 px-2 py-2"></th>
                  <th className="px-2 py-2 font-medium">run_id</th>
                  <th className="px-2 py-2 font-medium">{t('runs.table.strategy')}</th>
                  <th className="px-2 py-2 font-medium">{t('runs.table.gate')}</th>
                  {metricCols.map((m) => (
                    <th key={m} className="px-2 py-2 text-right font-medium">
                      {m}
                    </th>
                  ))}
                  <th className="px-2 py-2 font-medium">{t('runs.table.hypothesis')}</th>
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
                    className="cursor-pointer border-b border-border/60 bg-surface hover:bg-row focus:bg-row focus:outline-none"
                  >
                    <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(r.run_id)}
                        onChange={() => toggle(r.run_id)}
                        aria-label={t('runs.table.selectAria', { runId: r.run_id })}
                      />
                    </td>
                    <td className="px-2 py-2 font-mono text-xs tabular text-text">{r.run_id}</td>
                    <td className="px-2 py-2 font-mono text-xs text-text-secondary">{r.strategy ?? '—'}</td>
                    <td className="px-2 py-2">
                      <EnumBadge family="gate" value={r.gate_status} />
                    </td>
                    {metricCols.map((m) => (
                      <td key={m} className="px-2 py-2 text-right font-mono tabular">
                        {fmtMetric(r.metrics?.[m])}
                      </td>
                    ))}
                    <td className="max-w-[320px] truncate px-2 py-2 text-xs text-text-muted" title={r.hypothesis ?? undefined}>
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
        <div className="sticky bottom-0 mt-3 flex items-center gap-3 border border-border bg-panel px-4 py-2 text-sm">
          <span className="text-text-secondary">{t('runs.selected.count', { n: selected.size })}</span>
          <button
            disabled={selected.size < 2}
            onClick={() =>
              navigate(`/research/compare?run_ids=${[...selected].map(encodeURIComponent).join(',')}`)
            }
            className="border border-border px-3 py-1 font-mono text-xs uppercase tracking-[0.08em] text-text-secondary enabled:hover:border-border-strong enabled:hover:text-text disabled:opacity-40"
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
