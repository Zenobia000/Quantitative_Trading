/*
 * Monitor-zone shared bits — four-state query wrapper + KPI tile + simple table.
 * Keeps the Panel pages thin and consistent (mirrors RunReportPage's tile style).
 */
import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { PendingNote } from '@/components/PendingNote'
import { Skeleton } from '@/components/Skeleton'
import type { ApiResult } from '@/types/domain'
import { isPending } from '@/types/domain'

/** Render children only when real data is present; otherwise loading/error/pending/empty. */
export function QueryState<T>({
  q,
  pendingLabel,
  emptyLabel,
  children,
}: {
  q: UseQueryResult<ApiResult<T>>
  pendingLabel: string
  emptyLabel: string
  children: (data: T) => ReactNode
}) {
  if (q.isLoading) return <Skeleton className="h-24 w-full" />
  if (q.isError)
    return (
      <div className="rounded-lg border border-border bg-surface p-4 text-sm">
        <span className="text-error">載入失敗：{(q.error as Error)?.message}</span>
        <button
          onClick={() => q.refetch()}
          className="ml-3 rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          重試
        </button>
      </div>
    )
  if (isPending(q.data?.meta)) return <PendingNote label={pendingLabel} />
  const data = q.data?.data as T
  const empty = Array.isArray(data) ? data.length === 0 : data == null
  if (empty)
    return <div className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">{emptyLabel}</div>
  return <>{children(data)}</>
}

export function KpiCard({ label, value, pct, signed }: { label: string; value: unknown; pct?: boolean; signed?: boolean }) {
  const num = typeof value === 'number' ? value : null
  const tone = signed && num != null ? (num >= 0 ? 'text-gain' : 'text-loss') : 'text-text'
  const arrow = signed && num != null ? (num >= 0 ? '↑ ' : '↓ ') : ''
  const shown =
    num == null ? '—' : pct ? `${arrow}${(num * 100).toFixed(2)}%` : `${arrow}${Number.isInteger(num) ? num : num.toFixed(2)}`
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="text-xs text-text-muted">{label}</div>
      <div className={`mt-1 font-mono text-xl tabular ${tone}`}>{shown}</div>
    </div>
  )
}

export function SimpleTable<T>({
  rows,
  cols,
}: {
  rows: T[]
  cols: { key: string; label: string; fmt?: (v: unknown, row: T) => ReactNode }[]
}) {
  const cell = (row: T, key: string): unknown => (row as Record<string, unknown>)[key]
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-muted">
            {cols.map((c) => (
              <th key={c.key} className="px-3 py-2 font-medium">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border/50 last:border-0">
              {cols.map((c) => (
                <td key={c.key} className="px-3 py-1.5 font-mono tabular text-text-secondary">
                  {c.fmt ? c.fmt(cell(row, c.key), row) : String(cell(row, c.key) ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
