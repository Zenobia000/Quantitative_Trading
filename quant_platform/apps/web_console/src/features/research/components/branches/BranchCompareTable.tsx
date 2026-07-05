/*
 * 分支 vs parent compare delta 表（Goal 9）—— 複用後端 GET /research/branches/{id}/compare。
 *
 * 刻意「不導 /research/compare?run_ids=」既有頁：評測 run_id 只落在 evaluation ledger、不進 runs
 * 帳本，ComparePage（讀 /runs/compare）拿不到——故直接呈現後端 compare delta 表（誠實資料源，
 * 契約 §14.3 / task「compare 資料不齊則顯示後端 delta 表」）。
 * 未評測 → 提示「先評測」（parent 欄有值、branch/delta 為 null），非錯。
 */
import { useTranslation } from 'react-i18next'
import { Skeleton } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { useErrorText } from '@/i18n/useErrorText'
import { useBranchCompare } from '../../hooks/useBranches'
import type { BranchCompareRow } from '../../api/branches'

/** 靜態 class 對照（Tailwind JIT 不接受動態拼接的 class 名）。 */
const CHANGE_CLASS: Record<BranchCompareRow['change'], string> = {
  improved: 'text-gain',
  worsened: 'text-loss-aaa',
  flat: 'text-text-secondary',
}
const VERDICT_TONE = { branch_better: 'gain', parent_better: 'loss', inconclusive: 'muted' } as const

/** ratio 型（不 ×100）；其餘視為 fraction。 */
const RATIO_KEYS = new Set(['sharpe', 'sortino', 'calmar', 'oos_holdout_sharpe', 'dsr'])
const COUNT_KEYS = new Set(['trades'])

function fmt(key: string, v: number | null): string {
  if (v == null || !Number.isFinite(v)) return '—'
  if (COUNT_KEYS.has(key)) return String(Math.round(v))
  if (RATIO_KEYS.has(key)) return v.toFixed(3)
  return `${(v * 100).toFixed(2)}%`
}

function fmtDelta(key: string, v: number | null): string {
  if (v == null || !Number.isFinite(v)) return '—'
  const s = COUNT_KEYS.has(key)
    ? String(Math.round(v))
    : RATIO_KEYS.has(key)
      ? v.toFixed(3)
      : `${(v * 100).toFixed(2)}%`
  return v > 0 ? `+${s}` : s
}

export function BranchCompareTable({ branchId }: { branchId: string }) {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const { data, isLoading, isError, error, refetch } = useBranchCompare(branchId, true)

  if (isLoading) return <Skeleton className="h-24 w-full" />
  if (isError || !data)
    return (
      <div className="flex flex-wrap items-center gap-3 rounded-md border border-dashed border-border/70 bg-base p-3 text-xs text-text-muted">
        <span>{error ? errText(error) : t('branches.compare.error')}</span>
        <button
          onClick={() => refetch()}
          className="rounded-md border border-border px-2 py-0.5 text-text-secondary hover:text-text"
        >
          {t('common:action.retry')}
        </button>
      </div>
    )

  if (!data.branch_evaluated)
    return (
      <p
        data-testid="branch-compare-pending"
        className="rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-xs text-text-muted"
      >
        <span aria-hidden>◷ </span>
        {t('branches.compare.notEvaluated')}
      </p>
    )

  return (
    <div className="rounded-md border border-border bg-base p-3" data-testid="branch-compare-table">
      {data.decision && (
        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-text-muted">{t('branches.compare.decision')}</span>
          <StatusBadge tone={VERDICT_TONE[data.decision.verdict]}>
            {t(`branches.compare.verdict.${data.decision.verdict}`)}
          </StatusBadge>
          <span className="font-mono text-[11px] text-text-muted">
            {t('branches.compare.parentVsBranch', {
              parent: data.decision.parent_label ?? '—',
              branch: data.decision.branch_label ?? '—',
            })}
          </span>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="py-1 pr-3 font-medium">{t('branches.compare.metricCol')}</th>
              <th className="py-1 pr-3 text-right font-medium">{t('branches.compare.parentCol')}</th>
              <th className="py-1 pr-3 text-right font-medium">{t('branches.compare.branchCol')}</th>
              <th className="py-1 text-right font-medium">Δ</th>
            </tr>
          </thead>
          <tbody>
            {data.metrics.map((row) => (
              <tr key={row.metric} className="border-b border-border/40">
                <td className="py-1 pr-3 text-text">
                  {t(`branches.compare.metric.${row.metric}`, { defaultValue: row.metric })}
                </td>
                <td className="py-1 pr-3 text-right font-mono tabular text-text-secondary">
                  {fmt(row.metric, row.parent)}
                </td>
                <td className="py-1 pr-3 text-right font-mono tabular text-text">
                  {fmt(row.metric, row.branch)}
                </td>
                <td
                  className={`py-1 text-right font-mono tabular ${CHANGE_CLASS[row.change]}`}
                  data-testid={`branch-delta-${row.metric}`}
                >
                  {fmtDelta(row.metric, row.delta)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
