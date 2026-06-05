/*
 * 策略庫（/research/strategies）。三源對齊 assembly + design.pen frame + page spec。
 * strategy_list 接真實 GET /research/strategies（runs ledger projection）；四態完備。
 * version_timeline（版本沿革 + 假設 diff）需 /research/strategies/{id}/versions（needs-work）→ pending。
 */
import { useNavigate } from 'react-router-dom'
import { useStrategies } from '../hooks/useStrategies'
import type { StrategyRow } from '../api/strategies'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'

function statusTone(s: string): 'gain' | 'loss' | 'warning' | 'muted' {
  if (s === 'is_pass') return 'gain'
  if (s === 'is_fail') return 'loss'
  return 'muted'
}

function fmt(v: unknown): string {
  return typeof v === 'number' ? (Number.isInteger(v) ? String(v) : v.toFixed(2)) : '—'
}

export function StrategyLibraryPage() {
  const navigate = useNavigate()
  const { data, isLoading, isError, error, refetch } = useStrategies()
  const rows: StrategyRow[] = data?.data ?? []

  return (
    <div>
      <PageHeader title="策略庫" route="/research/strategies" subtitle="策略與版本沿革總覽" />

      {/* toolbar */}
      <div className="mb-3 flex items-center gap-2">
        <button
          onClick={() => navigate('/research/runs/new?new_strategy=1')}
          className="rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90"
        >
          新建策略
        </button>
        {rows.length > 0 && <span className="ml-auto text-xs text-text-muted tabular">{rows.length} 個策略</span>}
      </div>

      {/* strategy_list — 四態 */}
      {isLoading ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <SkeletonRows rows={3} cols={4} />
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">策略載入失敗：{(error as Error)?.message}</p>
          <button onClick={() => refetch()} className="mt-3 rounded-md border border-border px-3 py-1.5 hover:text-text">
            重試
          </button>
        </div>
      ) : rows.length === 0 ? (
        <FirstRunEmptyState onCta={() => navigate('/research/runs/new')} />
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((s) => (
            <button
              key={s.strategy_id}
              onClick={() => navigate(`/research/runs?strategy_id=${encodeURIComponent(s.strategy_id)}`)}
              className="rounded-lg border border-border bg-surface p-4 text-left hover:border-text/40"
            >
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold">{s.strategy_id}</h3>
                <span className="font-mono text-xs text-text-muted">{s.version}</span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <StatusBadge tone={statusTone(s.validation_status)}>{s.validation_status}</StatusBadge>
                <StatusBadge tone="muted">{s.stage}</StatusBadge>
                <span className="ml-auto text-xs text-text-muted tabular">{s.runs_count} runs</span>
              </div>
              <div className="mt-3 flex gap-4 font-mono text-xs text-text-secondary tabular">
                <span>Sharpe {fmt((s.best_kpi as Record<string, unknown>)?.sharpe)}</span>
                <span>CAGR {fmt((s.best_kpi as Record<string, unknown>)?.cagr)}</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* version_timeline — 版本沿革端點 needs-work */}
      <div className="mt-3">
        <PendingNote label="版本沿革 + 假設 diff（GET /research/strategies/{id}/versions，待後端）" />
      </div>
    </div>
  )
}
