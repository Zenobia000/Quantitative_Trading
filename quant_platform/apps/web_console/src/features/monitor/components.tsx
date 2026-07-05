/*
 * Monitor-zone shared bits — four-state query wrapper + KPI tile + simple table.
 * Keeps the Panel pages thin and consistent (mirrors RunReportPage's tile style).
 */
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { UseQueryResult } from '@tanstack/react-query'
import { PendingNote } from '@/components/PendingNote'
import { Skeleton } from '@/components/Skeleton'
import { StatCard } from '@/components/StatCard'
import { useErrorText } from '@/i18n/useErrorText'
import type { ApiMeta, ApiResult } from '@/types/domain'
import { isPending } from '@/types/domain'

/** Render children only when real data is present; otherwise loading/error/pending/empty. */
export function QueryState<T>({
  q,
  pendingLabel,
  emptyLabel,
  resource,
  children,
}: {
  q: UseQueryResult<ApiResult<T>>
  pendingLabel: string
  emptyLabel: string
  /** 錯誤文案的「載入失敗」主詞（如「運行看板」）；未給時回退為通用「資料」。 */
  resource?: string
  children: (data: T) => ReactNode
}) {
  const { t } = useTranslation(['common', 'errors', 'monitor'])
  const errText = useErrorText()
  if (q.isLoading) return <Skeleton className="h-24 w-full" />
  if (q.isError)
    return (
      <div className="border border-border bg-surface p-4 text-sm">
        <span className="text-error">
          {t('errors:load.failed', {
            resource: resource ?? t('monitor:queryState.resource'),
            detail: errText(q.error),
          })}
        </span>
        <button
          onClick={() => q.refetch()}
          className="ml-3 border border-border px-3 py-1 text-text-secondary hover:bg-input hover:text-text"
        >
          {t('common:action.retry')}
        </button>
      </div>
    )
  if (isPending(q.data?.meta)) return <PendingNote label={pendingLabel} />
  const data = q.data?.data as T
  const empty = Array.isArray(data) ? data.length === 0 : data == null
  if (empty)
    return <div className="border border-border bg-surface p-4 text-sm text-text-muted">{emptyLabel}</div>
  return (
    <>
      {children(data)}
      <EvidenceMetaStrip meta={q.data?.meta} />
    </>
  )
}

function EvidenceMetaStrip({ meta }: { meta: ApiMeta | undefined }) {
  if (!meta || Object.keys(meta).length === 0) return null
  const parts = [
    ['source', meta.data_source ?? '—'],
    ['as-of', meta.as_of ?? '—'],
    ['ttl', meta.ttl != null ? `${meta.ttl}s` : '—'],
    ['trace', meta.trace_id ?? '—'],
  ]
  if (meta.total != null) parts.splice(1, 0, ['total', String(meta.total)])
  return (
    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 border border-border bg-base px-2 py-1 font-mono text-[10px] uppercase tracking-[0.08em] text-text-muted">
      {parts.map(([k, v]) => (
        <span key={k}>
          {k}: <span className="text-text-secondary">{v}</span>
        </span>
      ))}
    </div>
  )
}

/** Monitor-zone KPI tile — thin adapter over the shared StatCard (single source of KPI styling). */
export function KpiCard({ label, value, pct, signed }: { label: string; value: unknown; pct?: boolean; signed?: boolean }) {
  return <StatCard label={label} value={typeof value === 'number' ? value : '—'} pct={pct} signed={signed} />
}

export function SimpleTable<T>({
  rows,
  cols,
}: {
  rows: T[]
  /** align：數值欄設 'right' 以對齊掃描（預設 left）。 */
  cols: { key: string; label: string; align?: 'left' | 'right'; fmt?: (v: unknown, row: T) => ReactNode }[]
}) {
  const cell = (row: T, key: string): unknown => (row as Record<string, unknown>)[key]
  const alignCls = (a?: 'left' | 'right') => (a === 'right' ? 'text-right' : 'text-left')
  return (
    <div className="overflow-x-auto border border-border bg-surface">
      <table className="w-full text-sm">
        {/* sticky 表頭：長表捲動時錨定欄名（scan aid） */}
        <thead>
          <tr className="border-b border-border bg-base font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
            {cols.map((c) => (
              <th key={c.key} className={`sticky top-0 z-10 bg-base px-3 py-2 font-medium ${alignCls(c.align)}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border/50 bg-surface last:border-0 hover:bg-row">
              {cols.map((c) => (
                <td key={c.key} className={`px-3 py-1.5 font-mono tabular text-text-secondary ${alignCls(c.align)}`}>
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
