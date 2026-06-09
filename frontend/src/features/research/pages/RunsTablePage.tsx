/*
 * Runs Table 研究主頁（/research/runs）。三源對齊：
 * - assembly/research_03_runs_table_integrated.md（結構/行為）
 * - design.pen「Research · Runs Table」frame（header/toolbar/guardrail/runs_table/multi_select/empty）
 * - pages/research_03_runs_table.md（四態/RWD/copy）
 * 資料：useRuns → GET /runs（shipped）。guardrail（trials/DSR）端點未接線 → pending（不假造數字）。
 * RWD：runs_table @<1024 橫向捲動「不轉 card」（研究級密集表）。
 */
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRuns } from '../hooks/useRuns'
import type { RunRow } from '../api/runs'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'

function statusTone(s?: string): 'gain' | 'loss' | 'warning' | 'error' | 'muted' {
  switch (s) {
    case 'done':
      return 'gain'
    case 'error':
    case 'failed':
      return 'error'
    case 'running':
    case 'validating':
    case 'queued':
      return 'warning'
    default:
      return 'muted'
  }
}

const METRIC_COLS = ['sharpe', 'cagr', 'mdd', 'win_rate', 'trades'] as const

function fmtMetric(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(2)
  return v == null ? '—' : String(v)
}

export function RunsTablePage() {
  const navigate = useNavigate()
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
    return out
  }, [data])
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const metricCols = useMemo(() => {
    const present = new Set<string>()
    for (const r of rows) for (const m of METRIC_COLS) if (r[m] != null) present.add(m)
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
      <PageHeader title="Runs Table" route="/research/runs" subtitle="研究主表 · single source of truth" />

      {/* research_toolbar */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button
          onClick={() => navigate('/research/runs/new')}
          className="rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90"
        >
          New Run
        </button>
        <span className="rounded-md border border-border px-2 py-1 text-xs text-text-secondary">
          Saved view：M0 候選 · 近 90 天
        </span>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-text-muted tabular">
            {rows.length ? `顯示 ${rows.length} 筆` : ''}
          </span>
          <button
            onClick={() => refetch()}
            className="rounded-md border border-border px-2 py-1 text-xs text-text-secondary hover:text-text"
            disabled={isFetching}
          >
            {isFetching ? '更新中…' : '重新整理'}
          </button>
        </div>
      </div>

      {/* guardrail_bar — trials/DSR/power gauge 端點未接線 */}
      <div className="mb-3">
        <PendingNote label="防過擬合護欄（累計試驗 / DSR / power gauge）" />
      </div>

      {/* runs_table — 四態 */}
      <section className="rounded-lg border border-border bg-surface">
        {isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={8} cols={4 + metricCols.length} />
          </div>
        ) : isError ? (
          <div className="p-6 text-sm">
            <p className="text-error">runs 載入失敗：{(error as Error)?.message ?? '未知錯誤'}</p>
            <button
              onClick={() => refetch()}
              className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
            >
              重試
            </button>
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8">
            <FirstRunEmptyState onCta={() => navigate('/research/runs/new')} />
          </div>
        ) : (
          // @<1024 橫向捲動保欄位密度（不轉 card）
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-muted">
                  <th className="w-8 p-2"></th>
                  <th className="p-2 font-medium">run_id</th>
                  <th className="p-2 font-medium">策略</th>
                  <th className="p-2 font-medium">狀態</th>
                  {metricCols.map((m) => (
                    <th key={m} className="p-2 text-right font-medium">
                      {m}
                    </th>
                  ))}
                  <th className="p-2 font-medium">建立時間</th>
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
                        aria-label={`選取 ${r.run_id}`}
                      />
                    </td>
                    <td className="p-2 font-mono text-xs tabular">{r.run_id}</td>
                    <td className="p-2 text-text-secondary">{r.strategy_id ?? '—'}</td>
                    <td className="p-2">
                      <StatusBadge tone={statusTone(r.status)}>{r.status ?? '—'}</StatusBadge>
                    </td>
                    {metricCols.map((m) => (
                      <td key={m} className="p-2 text-right font-mono tabular">
                        {fmtMetric(r[m])}
                      </td>
                    ))}
                    <td className="p-2 font-mono text-xs text-text-muted tabular">
                      {r.created_at ?? '—'}
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
          <span className="text-text-secondary">已選 {selected.size} 個 run</span>
          <button
            disabled={selected.size < 2}
            onClick={() =>
              navigate(`/research/compare?run_ids=${[...selected].map(encodeURIComponent).join(',')}`)
            }
            className="rounded-md border border-border px-3 py-1 text-text-secondary enabled:hover:text-text disabled:opacity-40"
          >
            比較（需 ≥2）
          </button>
          <button
            onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-text-muted hover:text-text"
          >
            清除
          </button>
        </div>
      )}
    </div>
  )
}
