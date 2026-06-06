/*
 * Sweep 參數掃描（/research/sweep）。三源對齊 assembly + design.pen frame + page spec。
 * estimate_guard 接真實 GET /runs/estimate（提交前估算 N configs / est min）；
 * sweep 提交（POST /research/sweep）+ heatmap/cell_drilldown 為 needs-work（async job）→ pending。
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getEstimate } from '../api/estimate'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'

const field = 'w-full rounded-md border border-border bg-input px-3 py-1.5 text-sm font-mono'
const label = 'mb-1 block text-xs text-text-secondary'

export function SweepPage() {
  const [grid, setGrid] = useState<Record<string, string>>({
    box_period: '40,60,80',
    entry_confirm_days: '1,2',
  })

  const est = useQuery({
    queryKey: ['estimate', grid],
    queryFn: () => getEstimate(grid),
    staleTime: 0,
  })
  const e = est.data?.data

  const setAxis = (k: string, v: string) => setGrid((g) => ({ ...g, [k]: v }))

  return (
    <div>
      <PageHeader title="Sweep 參數掃描" route="/research/sweep" subtitle="range/step 向量化掃描 · 找穩健高原非單點尖峰" />

      {/* sweep_config */}
      <section className="mb-3 grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        {Object.entries(grid).map(([k, v]) => (
          <div key={k}>
            <label className={label}>{k}（逗號列，每值一格）</label>
            <input className={field} value={v} onChange={(ev) => setAxis(k, ev.target.value)} />
          </div>
        ))}
      </section>

      {/* estimate_guard — 真接 /runs/estimate */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        {est.isLoading ? (
          <span className="text-sm text-text-muted">估算中…</span>
        ) : est.isError ? (
          <span className="text-sm text-error">估算失敗：{(est.error as Error)?.message}</span>
        ) : e ? (
          <div className="flex items-center gap-4">
            <span className="font-mono text-lg tabular">
              will run <span className="text-text">{e.n_configs}</span> configs · est{' '}
              <span className="text-text">{e.est_minutes}</span> min
            </span>
            {e.n_configs > 200 && (
              <span className="text-sm text-warning">⚠ config 數過大，建議收窄 range</span>
            )}
          </div>
        ) : null}
      </section>

      {/* 提交 + 結果（async job，needs-work M3.5）→ pending */}
      <div className="flex flex-col gap-2">
        <PendingNote label="提交掃描（POST /research/sweep async job）" />
        <PendingNote label="Optimization heatmap 穩定區（掃描結果，需 job 完成）" />
        <PendingNote label="Cell drilldown（點 cell → run 摘要）" />
      </div>
    </div>
  )
}
