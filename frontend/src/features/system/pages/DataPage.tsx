/*
 * System — 資料管理（system_data）。
 * 三塊互動：**ingest 觸發**（POST /system/ingest async → 輪詢 status，8.H.6）、
 * **universe build 觸發**（POST /system/universe/build async → 輪詢，ADR-032）、
 * **bundle 清單**（GET /system/bundles，真實 manifest 掃描；無資料 → typed-empty，
 * 絕不假造 GOAL.md #8）。
 */
import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
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
      <div className="mb-2 text-sm font-medium">觸發 Ingest（async job）</div>
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          股票（逗號分隔）
          <input className={`${inputCls} w-48`} value={symbols} onChange={(e) => setSymbols(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          起<input className={inputCls} value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          迄<input className={inputCls} value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          來源
          <select className={inputCls} value={source} onChange={(e) => setSource(e.target.value as 'finlab' | 'finmind')}>
            <option value="finlab">finlab</option>
            <option value="finmind">finmind</option>
          </select>
        </label>
        <button onClick={submit} disabled={trigger.isPending} className={btnCls}>
          {trigger.isPending ? '送出中…' : '開始 Ingest'}
        </button>
      </div>
      {trigger.isError && <div className="mt-2 text-sm text-error">送出失敗：{(trigger.error as Error)?.message}</div>}
      {jobId && (
        <div className="mt-3 rounded-md border border-border bg-base p-2 font-mono text-xs text-text-secondary">
          {status.isError ? (
            // A4：未知/過期 job → 404，顯示錯誤而非無盡「…」。
            <span className="text-error">job {jobId} 狀態查詢失敗：{(status.error as Error)?.message}（可能已過期或不存在）</span>
          ) : (
            <>
              job <span className="text-text">{jobId}</span> · 狀態 <span className="text-text">{job?.status ?? '…'}</span>
              {job?.result && <span> · ok {job.result.ok?.length ?? 0} / failed {job.result.failed?.length ?? 0}</span>}
            </>
          )}
        </div>
      )}
    </section>
  )
}

function UniverseBuildCard() {
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
      <div className="mb-2 text-sm font-medium">建置 Universe（survivorship-clean，async job）</div>
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          策略<input className={`${inputCls} w-36`} value={strategy} onChange={(e) => setStrategy(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          起<input className={inputCls} value={spanStart} onChange={(e) => setSpanStart(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-muted">
          迄<input className={inputCls} value={spanEnd} onChange={(e) => setSpanEnd(e.target.value)} />
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
          {trigger.isPending ? '送出中…' : '開始建置'}
        </button>
      </div>
      {trigger.isError && <div className="mt-2 text-sm text-error">送出失敗：{(trigger.error as Error)?.message}</div>}
      {jobId && (
        <div className="mt-3 rounded-md border border-border bg-base p-2 font-mono text-xs text-text-secondary">
          {status.isError ? (
            // A4：未知/過期 job → 404，顯示錯誤而非無盡「…」。
            <span className="text-error">job {jobId} 狀態查詢失敗：{(status.error as Error)?.message}（可能已過期或不存在）</span>
          ) : (
            <>
              job <span className="text-text">{jobId}</span> · 狀態 <span className="text-text">{job?.status ?? '…'}</span>
              {job?.result && (
                <span>
                  {' '}
                  · {job.result.n_symbols ?? 0} 檔（alive {job.result.n_alive ?? 0} / delisted {job.result.n_delisted ?? 0}）
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
  const bundles = useBundles()

  return (
    <div>
      <PageHeader title="資料管理" route="/system/data" subtitle="ingest + universe build 觸發 · bundle 清單" />

      <IngestCard />
      <UniverseBuildCard />

      {/* bundle manifest — 真實掃描 data/parquet* 的 manifest（無資料 → typed-empty） */}
      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">Bundle 清單</div>
        <QueryState q={bundles} pendingLabel="bundle manifest（待 producer）" emptyLabel="尚無 bundle（data/parquet* 無 manifest）">
          {(rows: BundleRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'id', label: 'Bundle' },
                { key: 'kind', label: '類型' },
                { key: 'stock_count', label: '檔數' },
                { key: 'coverage_start', label: '起' },
                { key: 'coverage_end', label: '迄' },
                { key: 'strategy', label: '策略' },
              ]}
            />
          )}
        </QueryState>
      </section>
    </div>
  )
}
