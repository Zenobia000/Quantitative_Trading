/*
 * Compare（/research/compare?run_ids=a,b,c）。三源對齊 assembly + design.pen frame + page spec。
 * design.pen sections: header / compare_toolbar / guardrail_bar / equity_overlay / metric_diff_table / parallel_coordinates。
 * 資料：useCompare → GET /runs/compare?baseline=&run_ids=（shipped；回應為「物件」
 * {baseline_id, metric_keys, comparisons[...]}，每列含 metrics/delta/rank/gate_status）。
 * equity_overlay / parcoords / guardrail 端點未接線 → pending（不假造數字）。
 */
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useCompare } from '../hooks/useCompare'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { useErrorText } from '@/i18n/useErrorText'

function fmt(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(2)
  return v == null ? '—' : String(v)
}

function fmtDelta(v: number): string {
  const s = Number.isInteger(v) ? String(v) : v.toFixed(2)
  return v > 0 ? `+${s}` : s
}

export function ComparePage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const [sp] = useSearchParams()
  const runIds = (sp.get('run_ids') ?? '').split(',').map((s) => s.trim()).filter(Boolean)
  const baseline = runIds[0]
  const { data, isLoading, isError, error, refetch } = useCompare(baseline, runIds, runIds.length > 0)

  if (runIds.length < 2)
    return (
      <div>
        <PageHeader title={t('compare.title')} route="/research/compare" />
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-text-secondary">
          {t('compare.needTwo')}
          <button
            onClick={() => navigate('/research/runs')}
            className="ml-2 rounded-md border border-border px-3 py-1 hover:text-text"
          >
            {t('compare.backToRuns')}
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
      <PageHeader title={t('compare.title')} route="/research/compare" subtitle={t('compare.subtitle')} />

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
          {t('compare.editSweep')}
        </button>
      </div>

      {/* guardrail_bar */}
      <div className="mb-3">
        <PendingNote label={t('compare.pending.guardrail')} />
      </div>

      {/* equity_overlay */}
      <div className="mb-3">
        <PendingNote label={t('compare.pending.equityOverlay')} />
      </div>

      {/* metric_diff_table — 每列一個 run，欄為 metric_keys（非 baseline 顯示 delta） */}
      <section className="mb-3 rounded-lg border border-border bg-surface">
        {isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={4} cols={4} />
          </div>
        ) : isError ? (
          <div className="p-6 text-sm">
            <p className="text-error">
              {t('errors:load.failed', { resource: t('compare.resource'), detail: errText(error) })}
            </p>
            <button onClick={() => refetch()} className="mt-3 rounded-md border border-border px-3 py-1.5 hover:text-text">
              {t('common:action.retry')}
            </button>
          </div>
        ) : comparisons.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-muted">
                  <th className="p-2 font-medium">{t('compare.table.run')}</th>
                  <th className="p-2 font-medium">{t('compare.table.gate')}</th>
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
                        <EnumBadge family="gate" value={c.gate_status} />
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
          <div className="p-6 text-sm text-text-muted">{t('compare.empty')}</div>
        )}
      </section>

      {/* parallel_coordinates */}
      <PendingNote label={t('compare.pending.parcoords')} />
    </div>
  )
}
