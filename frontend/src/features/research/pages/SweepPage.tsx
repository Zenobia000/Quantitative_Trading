/*
 * Sweep 參數掃描（/research/sweep）。三源對齊 assembly + design.pen frame + page spec。
 * estimate_guard 接真實 GET /runs/estimate（提交前估算 N configs / est min）；
 * 提交接真實 POST /research/sweep（async job）+ GET /research/sweep/{id}/status（輪詢 grid-plan 展開）。
 * heatmap / cell_drilldown 需 per-config 回測（parquet）→ 仍 pending。
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { getEstimate } from '../api/estimate'
import { useSubmitSweep, useSweepStatus } from '../hooks/useSweep'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { EnumBadge } from '@/components/EnumBadge'
import { useErrorText } from '@/i18n/useErrorText'

const field = 'w-full rounded-md border border-border bg-input px-3 py-1.5 text-sm font-mono'
const label = 'mb-1 block text-xs text-text-secondary'

/** 逗號列 grid → 陣列 grid（submit 用）。 */
function toArrayGrid(grid: Record<string, string>): Record<string, string[]> {
  const out: Record<string, string[]> = {}
  for (const [k, v] of Object.entries(grid)) {
    const vals = v.split(',').map((s) => s.trim()).filter(Boolean)
    if (vals.length) out[k] = vals
  }
  return out
}

export function SweepPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const [grid, setGrid] = useState<Record<string, string>>({
    box_period: '40,60,80',
    entry_confirm_days: '1,2',
  })
  const [jobId, setJobId] = useState<string | undefined>(undefined)

  const est = useQuery({
    queryKey: ['estimate', grid],
    queryFn: () => getEstimate(grid),
    staleTime: 0,
  })
  const e = est.data?.data

  const submit = useSubmitSweep()
  const job = useSweepStatus(jobId)
  const jobData = job.data?.data

  const setAxis = (k: string, v: string) => setGrid((g) => ({ ...g, [k]: v }))
  const onSubmit = () =>
    submit.mutate(toArrayGrid(grid), { onSuccess: (res) => setJobId(res.data?.job_id) })

  return (
    <div>
      <PageHeader title={t('sweep.title')} route="/research/sweep" subtitle={t('sweep.subtitle')} />

      {/* sweep_config */}
      <section className="mb-3 grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        {Object.entries(grid).map(([k, v]) => (
          <div key={k}>
            <label className={label}>{t('sweep.axisLabel', { axis: k })}</label>
            <input className={field} value={v} onChange={(ev) => setAxis(k, ev.target.value)} />
          </div>
        ))}
      </section>

      {/* estimate_guard — 真接 /runs/estimate */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        {est.isLoading ? (
          <span className="text-sm text-text-muted">{t('sweep.estimating')}</span>
        ) : est.isError ? (
          <span className="text-sm text-error">{t('sweep.estimateError', { detail: errText(est.error) })}</span>
        ) : e ? (
          <div className="flex flex-wrap items-center gap-4">
            <span className="font-mono text-lg tabular text-text">
              {t('sweep.estimate', { configs: e.n_configs, minutes: e.est_minutes })}
            </span>
            {e.n_configs > 200 && <span className="text-sm text-warning">{t('sweep.warnTooMany')}</span>}
            <button
              onClick={onSubmit}
              disabled={submit.isPending}
              className="ml-auto rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90 disabled:opacity-50"
            >
              {submit.isPending ? t('sweep.submitting') : t('sweep.submit')}
            </button>
          </div>
        ) : null}
      </section>

      {/* sweep job status — 真接 POST /research/sweep + 輪詢 */}
      {(jobId || submit.isError) && (
        <section className="mb-3 rounded-lg border border-border bg-surface p-4 text-sm">
          {submit.isError ? (
            <span className="text-error">{t('sweep.submitError', { detail: errText(submit.error) })}</span>
          ) : job.isError ? (
            // A4：未知/過期 job → 後端 404，顯示錯誤訊息而非無盡 queued。
            <span className="text-error">{t('sweep.jobError', { detail: errText(job.error), jobId })}</span>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <EnumBadge family="job" value={jobData?.status ?? 'queued'} />
              <span className="font-mono text-xs text-text-muted tabular">job {jobId}</span>
              {jobData?.status === 'done' && jobData.result && (
                <span className="font-mono tabular text-text">
                  {t('sweep.expanded', { n: jobData.result.n_configs })}
                </span>
              )}
              {jobData?.error && <span className="text-error">{jobData.error}</span>}
            </div>
          )}
        </section>
      )}

      {/* 結果視覺化（needs per-config 回測，parquet）→ pending */}
      <div className="flex flex-col gap-2">
        <PendingNote label={t('sweep.pending.heatmap')} />
        <PendingNote label={t('sweep.pending.drilldown')} />
      </div>
    </div>
  )
}
