/*
 * Compare（/research/compare?run_ids=a,b,c）。三源對齊 assembly + design.pen frame + page spec。
 * design.pen sections: header / compare_toolbar / guardrail_bar / equity_overlay / metric_diff_table / parallel_coordinates。
 * 資料：useCompare → GET /runs/compare?baseline=&run_ids=（shipped；回應為「物件」
 * {baseline_id, metric_keys, comparisons[...]}，每列含 metrics/delta/rank/gate_status）。
 * equity_overlay / parcoords / guardrail 端點未接線 → pending（不假造數字）。
 */
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useCompare } from '../hooks/useCompare'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'

function fmt(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(2)
  return v == null ? '—' : String(v)
}

function fmtDelta(v: number): string {
  const s = Number.isInteger(v) ? String(v) : v.toFixed(2)
  return v > 0 ? `+${s}` : s
}

function gateTone(s?: string | null): 'gain' | 'error' | 'warning' | 'muted' {
  if (s === 'PASS') return 'gain'
  if (s === 'FAIL') return 'error'
  if (s === 'INCOMPLETE') return 'warning'
  return 'muted'
}

export function ComparePage() {
  const navigate = useNavigate()
  const [sp] = useSearchParams()
  const runIds = (sp.get('run_ids') ?? '').split(',').map((s) => s.trim()).filter(Boolean)
  const baseline = runIds[0]
  const { data, isLoading, isError, error, refetch } = useCompare(baseline, runIds, runIds.length > 0)

  if (runIds.length < 2)
    return (
      <div>
        <PageHeader title="Compare" route="/research/compare" />
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-text-secondary">
          請至少選 2 個 run 比較。
          <button
            onClick={() => navigate('/research/runs')}
            className="ml-2 rounded-md border border-border px-3 py-1 hover:text-text"
          >
            回 Runs Table
          </button>
        </div>
      </div>
    )

  const report = data?.data
  const baselineId = report?.baseline_id ?? baseline
  const metricKeys = report?.metric_keys ?? []
  const comparisons = report?.comparisons ?? []

  return (
    <div>
      <PageHeader title="Compare" route="/research/compare" subtitle="多 run 並排 · 找穩健高原非單點尖峰" />

      {/* compare_toolbar */}
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        {runIds.map((id) => (
          <span
            key={id}
            className={`rounded-md border px-2 py-1 font-mono tabular ${
              id === baselineId ? 'border-text text-text' : 'border-border text-text-secondary'
            }`}
          >
            {id === baselineId ? '★ ' : ''}
            {id}
          </span>
        ))}
        <button
          onClick={() => navigate('/research/sweep')}
          className="ml-auto rounded-md border border-border px-2 py-1 text-text-secondary hover:text-text"
        >
          改掃描參數
        </button>
      </div>

      {/* guardrail_bar */}
      <div className="mb-3">
        <PendingNote label="防 cherry-pick 護欄（試驗數 / DSR / power gauge）" />
      </div>

      {/* equity_overlay */}
      <div className="mb-3">
        <PendingNote label="Equity 疊圖（多 run，單色明度階）" />
      </div>

      {/* metric_diff_table — 每列一個 run，欄為 metric_keys（非 baseline 顯示 delta） */}
      <section className="mb-3 rounded-lg border border-border bg-surface">
        {isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={4} cols={4} />
          </div>
        ) : isError ? (
          <div className="p-6 text-sm">
            <p className="text-error">比較載入失敗：{(error as Error)?.message ?? '未知錯誤'}</p>
            <button onClick={() => refetch()} className="mt-3 rounded-md border border-border px-3 py-1.5 hover:text-text">
              重試
            </button>
          </div>
        ) : comparisons.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-muted">
                  <th className="p-2 font-medium">run</th>
                  <th className="p-2 font-medium">Gate</th>
                  {metricKeys.map((k) => (
                    <th key={k} className="p-2 text-right font-medium">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisons.map((c) => {
                  const metrics = (c.metrics ?? {}) as Record<string, unknown>
                  const delta = (c.delta ?? {}) as Record<string, unknown>
                  return (
                    <tr key={c.run_id} className="border-b border-border/60">
                      <td className="p-2 font-mono text-xs tabular">
                        {c.is_baseline ? '★ ' : ''}
                        {c.run_id}
                      </td>
                      <td className="p-2">
                        <StatusBadge tone={gateTone(c.gate_status)}>{c.gate_status ?? '—'}</StatusBadge>
                      </td>
                      {metricKeys.map((k) => {
                        const d = delta[k]
                        return (
                          <td key={k} className="p-2 text-right font-mono text-xs tabular">
                            {fmt(metrics[k])}
                            {!c.is_baseline && typeof d === 'number' && (
                              <span className={d >= 0 ? 'ml-1 text-gain' : 'ml-1 text-loss'}>({fmtDelta(d)})</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-text-muted">無可比較的 run（ledger 為空或 run_ids 未命中）。</div>
        )}
      </section>

      {/* parallel_coordinates */}
      <PendingNote label="Parallel coordinates（參數×指標 brushing，找穩健高原）" />
    </div>
  )
}
