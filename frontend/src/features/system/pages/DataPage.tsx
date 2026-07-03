/*
 * System — 資料管理（system_data）。
 * 三塊互動：**ingest 觸發**（POST /system/ingest async → 輪詢 status，8.H.6）、
 * **universe build 觸發**（POST /system/universe/build async → 輪詢，ADR-032）、
 * **bundle 清單**（GET /system/bundles，真實 manifest 掃描；無資料 → typed-empty，
 * 絕不假造 GOAL.md #8）。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { EnumBadge } from '@/components/EnumBadge'
import { useErrorText } from '@/i18n/useErrorText'
import { QueryState, SimpleTable } from '@/features/monitor/components'
import {
  useBundles,
  useIngestStatus,
  useTriggerIngest,
  useTriggerUniverseBuild,
  useUniverseBuildStatus,
} from '../hooks/useSystem'
import type { BundleRow } from '../hooks/useSystem'

const inputCls = 'rounded-md border border-border bg-base px-2 py-1 font-mono text-sm text-text'
const btnCls =
  'rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90 disabled:opacity-50'

function IngestCard() {
  const { t } = useTranslation('system')
  const errText = useErrorText()
  const trigger = useTriggerIngest()
  const [jobId, setJobId] = useState<string | null>(null)
  const status = useIngestStatus(jobId)

  const [symbols, setSymbols] = useState('2330,2317')
  const [start, setStart] = useState('2023-01-01')
  const [end, setEnd] = useState('2023-12-31')
  const [source, setSource] = useState<'finlab' | 'finmind'>('finlab')

  const submit = () => {
    const syms = symbols.split(',').map((s) => s.trim()).filter(Boolean)
    trigger.mutate({ symbols: syms, start, end, source }, { onSuccess: (res) => setJobId(res.data.job_id) })
  }
  const job = status.data?.data

  return (
    <section className="mb-4 rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 text-sm font-medium">{t('data.ingest.heading')}</div>
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          {t('data.ingest.symbols')}
          <input className={`${inputCls} w-48`} value={symbols} onChange={(e) => setSymbols(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          {t('data.field.start')}
          <input className={inputCls} value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          {t('data.field.end')}
          <input className={inputCls} value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          {t('data.ingest.source')}
          <select className={inputCls} value={source} onChange={(e) => setSource(e.target.value as 'finlab' | 'finmind')}>
            <option value="finlab">finlab</option>
            <option value="finmind">finmind</option>
          </select>
        </label>
        <button onClick={submit} disabled={trigger.isPending} className={btnCls}>
          {trigger.isPending ? t('data.action.submitting') : t('data.ingest.submit')}
        </button>
      </div>
      {trigger.isError && (
        <div className="mt-2 text-sm text-error">{t('data.action.submitFailed', { detail: errText(trigger.error) })}</div>
      )}
      {jobId && (
        <div className="mt-3 rounded-md border border-border bg-base p-2 font-mono text-xs text-text-secondary">
          {status.isError ? (
            // A4：未知/過期 job → 404，顯示錯誤而非無盡「…」（契約側語意，i18n 本地化）。
            <span className="text-error">{t('data.job.error', { jobId, detail: errText(status.error) })}</span>
          ) : (
            <>
              {t('data.job.label')} <span className="text-text">{jobId}</span> · {t('data.job.statusLabel')}{' '}
              <EnumBadge family="job" value={job?.status} />
              {job?.result && (
                <span> · {t('data.ingest.result', { ok: job.result.ok?.length ?? 0, failed: job.result.failed?.length ?? 0 })}</span>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}

function UniverseBuildCard() {
  const { t } = useTranslation('system')
  const errText = useErrorText()
  const trigger = useTriggerUniverseBuild()
  const [jobId, setJobId] = useState<string | null>(null)
  const status = useUniverseBuildStatus(jobId)

  const [strategy, setStrategy] = useState('inst_flow')
  const [spanStart, setSpanStart] = useState('2010-01-01')
  const [spanEnd, setSpanEnd] = useState('2024-12-31')
  const [topN, setTopN] = useState('200')
  const [minTurnover, setMinTurnover] = useState('50000000')
  const [cacheDir, setCacheDir] = useState('data/parquet_finlab_universe')

  const submit = () => {
    trigger.mutate(
      {
        strategy,
        span_start: spanStart,
        span_end: spanEnd,
        top_n: Number(topN),
        min_turnover: Number(minTurnover),
        cache_dir: cacheDir,
      },
      { onSuccess: (res) => setJobId(res.data.job_id) },
    )
  }
  const job = status.data?.data

  return (
    <section className="mb-4 rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 text-sm font-medium">{t('data.universe.heading')}</div>
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          {t('data.field.strategy')}
          <input className={`${inputCls} w-36`} value={strategy} onChange={(e) => setStrategy(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          {t('data.field.start')}
          <input className={inputCls} value={spanStart} onChange={(e) => setSpanStart(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          {t('data.field.end')}
          <input className={inputCls} value={spanEnd} onChange={(e) => setSpanEnd(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          top_n<input className={`${inputCls} w-20`} value={topN} onChange={(e) => setTopN(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          min_turnover
          <input className={`${inputCls} w-32`} value={minTurnover} onChange={(e) => setMinTurnover(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          cache_dir
          <input className={`${inputCls} w-56`} value={cacheDir} onChange={(e) => setCacheDir(e.target.value)} />
        </label>
        <button onClick={submit} disabled={trigger.isPending} className={btnCls}>
          {trigger.isPending ? t('data.action.submitting') : t('data.universe.submit')}
        </button>
      </div>
      {trigger.isError && (
        <div className="mt-2 text-sm text-error">{t('data.action.submitFailed', { detail: errText(trigger.error) })}</div>
      )}
      {jobId && (
        <div className="mt-3 rounded-md border border-border bg-base p-2 font-mono text-xs text-text-secondary">
          {status.isError ? (
            // A4：未知/過期 job → 404，顯示錯誤而非無盡「…」（契約側語意，i18n 本地化）。
            <span className="text-error">{t('data.job.error', { jobId, detail: errText(status.error) })}</span>
          ) : (
            <>
              {t('data.job.label')} <span className="text-text">{jobId}</span> · {t('data.job.statusLabel')}{' '}
              <EnumBadge family="job" value={job?.status} />
              {job?.result && (
                <span>
                  {' '}
                  · {t('data.universe.result', {
                    n: job.result.n_symbols ?? 0,
                    alive: job.result.n_alive ?? 0,
                    delisted: job.result.n_delisted ?? 0,
                  })}
                </span>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}

export function DataPage() {
  const { t } = useTranslation('system')
  const bundles = useBundles()

  return (
    <div>
      <PageHeader title={t('data.title')} route="/system/data" subtitle={t('data.subtitle')} />

      <IngestCard />
      <UniverseBuildCard />

      {/* bundle manifest — 真實掃描 data/parquet* 的 manifest（無資料 → typed-empty） */}
      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('data.bundles.heading')}</div>
        <QueryState q={bundles} pendingLabel={t('data.bundles.pending')} emptyLabel={t('data.bundles.empty')}>
          {(rows: BundleRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'id', label: t('data.bundles.col.id') },
                { key: 'kind', label: t('data.bundles.col.kind') },
                { key: 'stock_count', label: t('data.bundles.col.stockCount') },
                { key: 'coverage_start', label: t('data.field.start') },
                { key: 'coverage_end', label: t('data.field.end') },
                { key: 'strategy', label: t('data.field.strategy') },
              ]}
            />
          )}
        </QueryState>
      </section>
    </div>
  )
}
