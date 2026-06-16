/*
 * System — 資料管理（system_data）。
 * Bundle 清單（/system/bundles，pending）+ **互動 ingest 觸發**（POST /system/ingest
 * async → 輪詢 status，8.H.6）。資料活水未接時 bundle 為 pending；ingest 表單即可用。
 */
import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { QueryState, SimpleTable } from '@/features/monitor/components'
import { useBundles, useIngestStatus, useTriggerIngest } from '../hooks/useSystem'

export function DataPage() {
  const bundles = useBundles()
  const trigger = useTriggerIngest()
  const [jobId, setJobId] = useState<string | null>(null)
  const status = useIngestStatus(jobId)

  const [symbols, setSymbols] = useState('2330,2317')
  const [start, setStart] = useState('2023-01-01')
  const [end, setEnd] = useState('2023-12-31')
  const [source, setSource] = useState<'finlab' | 'finmind'>('finlab')

  const submit = () => {
    const syms = symbols.split(',').map((s) => s.trim()).filter(Boolean)
    trigger.mutate(
      { symbols: syms, start, end, source },
      { onSuccess: (res) => setJobId(res.data.job_id) },
    )
  }

  const job = status.data?.data
  const inputCls = 'rounded-md border border-border bg-base px-2 py-1 font-mono text-sm text-text'

  return (
    <div>
      <PageHeader title="資料管理" route="/system/data" subtitle="bundle 清單 + ingest 觸發" />

      {/* ingest trigger (real async job, 8.H.6) */}
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
          <button
            onClick={submit}
            disabled={trigger.isPending}
            className="rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90 disabled:opacity-50"
          >
            {trigger.isPending ? '送出中…' : '開始 Ingest'}
          </button>
        </div>
        {trigger.isError && <div className="mt-2 text-sm text-error">送出失敗：{(trigger.error as Error)?.message}</div>}
        {jobId && (
          <div className="mt-3 rounded-md border border-border bg-base p-2 font-mono text-xs text-text-secondary">
            job <span className="text-text">{jobId}</span> · 狀態 <span className="text-text">{job?.status ?? '…'}</span>
            {job?.result && (
              <span> · ok {job.result.ok?.length ?? 0} / failed {job.result.failed?.length ?? 0}</span>
            )}
          </div>
        )}
      </section>

      {/* bundle manifest */}
      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">Bundle 清單</div>
        <QueryState q={bundles} pendingLabel="bundle manifest（待 producer）" emptyLabel="尚無 bundle">
          {(rows: unknown[]) => (
            <SimpleTable
              rows={rows as Record<string, unknown>[]}
              cols={[
                { key: 'bundle_id', label: 'Bundle' },
                { key: 'symbols', label: '檔數' },
                { key: 'start', label: '起' },
                { key: 'end', label: '迄' },
                { key: 'updated_at', label: '更新' },
              ]}
            />
          )}
        </QueryState>
      </section>
    </div>
  )
}
