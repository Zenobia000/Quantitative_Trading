/*
 * Compare ledger（/research/compare?run_ids=a,b,c）。
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

function gateCounts(rows: Array<{ gate_status?: string | null }>): { pass: number; fail: number; other: number } {
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
  const gates = gateCounts(comparisons)

  return (
    <div>
      <PageHeader title={t('compare.title')} route="/research/compare" subtitle={t('compare.subtitle')} />

      <div className="mb-3 border border-border bg-panel">
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-text-muted">Comparison Ledger</div>
            <div className="mt-0.5 text-xs text-text-secondary">{t('compare.subtitle')}</div>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2 font-mono text-[11px] uppercase tracking-[0.08em]">
            <span className="border border-info/50 px-2 py-1 text-info">BASE {baselineId}</span>
            <span className="border border-border px-2 py-1 text-text-secondary">RUNS {runIds.length}</span>
            <span className="border border-gain/40 px-2 py-1 text-gain">PASS {gates.pass}</span>
            <span className="border border-loss/40 px-2 py-1 text-loss">FAIL {gates.fail}</span>
            <span className="border border-border px-2 py-1 text-text-muted">OTHER {gates.other}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1 px-3 py-2">
          {runIds.map((id) => (
            <span
              key={id}
              className={`border px-2 py-1 font-mono text-xs tabular ${
                id === baselineId ? 'border-info bg-input text-text' : 'border-border text-text-secondary'
              }`}
            >
              {id === baselineId ? '★ ' : ''}
              {id}
            </span>
          ))}
          <button
            onClick={() => navigate('/research/sweep')}
            className="ml-auto border border-border px-2 py-1 font-mono text-xs uppercase tracking-[0.08em] text-text-secondary hover:border-border-strong hover:text-text"
          >
            {t('compare.editSweep')}
          </button>
        </div>
      </div>

      <div className="mb-3 grid gap-2 lg:grid-cols-3">
        <PendingNote label={t('compare.pending.guardrail')} />
        <PendingNote label={t('compare.pending.equityOverlay')} />
        <PendingNote label={t('compare.pending.parcoords')} />
      </div>

      <section className="mb-3 border border-border bg-panel">
        {isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={4} cols={4} />
          </div>
        ) : isError ? (
          <div className="p-6 text-sm">
            <p className="text-error">
              {t('errors:load.failed', { resource: t('compare.resource'), detail: errText(error) })}
            </p>
            <button onClick={() => refetch()} className="mt-3 border border-border px-3 py-1.5 hover:border-border-strong hover:text-text">
              {t('common:action.retry')}
            </button>
          </div>
        ) : comparisons.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="border-b border-border bg-base text-left font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                  <th className="px-2 py-2 font-medium">{t('compare.table.run')}</th>
                  <th className="px-2 py-2 font-medium">{t('compare.table.gate')}</th>
                  {metricKeys.map((k) => (
                    <th key={k} className="px-2 py-2 text-right font-medium">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisons.map((c) => {
                  const metrics = (c.metrics ?? {}) as Record<string, unknown>
                  const delta = (c.delta ?? {}) as Record<string, unknown>
                  return (
                    <tr key={c.run_id} className="border-b border-border/60 bg-surface hover:bg-row">
                      <td className="px-2 py-2 font-mono text-xs tabular text-text">
                        {c.is_baseline ? '★ ' : ''}
                        {c.run_id}
                      </td>
                      <td className="px-2 py-2">
                        <EnumBadge family="gate" value={c.gate_status} />
                      </td>
                      {metricKeys.map((k) => {
                        const d = delta[k]
                        return (
                          <td key={k} className="px-2 py-2 text-right font-mono text-xs tabular">
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
    </div>
  )
}
