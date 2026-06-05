/*
 * New Run 設定（/research/runs/new）。三源對齊 assembly + design.pen frame + page spec。
 * 接真實 POST /runs（shipped；RunCreateRequest 型別取自 OpenAPI）。提交成功 → 跳 Run Report。
 * 注意：v0.6 後端 RunCreateRequest 為精簡版（hypothesis/preset/stocks/IS 區間/engine）；
 * 完整 13 參數 / 成本攤平 / range-step / OOS 鎖死待後端擴充 RunConfig（companion 後端 goal）。
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { createRun, type RunCreateRequest } from '../api/createRun'
import { ApiError } from '@/services/http'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'

const field = 'w-full rounded-md border border-border bg-input px-3 py-1.5 text-sm'
const label = 'mb-1 block text-xs text-text-secondary'

export function NewRunPage() {
  const navigate = useNavigate()
  const [hypothesis, setHypothesis] = useState('')
  const [preset, setPreset] = useState('v3')
  const [stocks, setStocks] = useState('2330,2454')
  const [isStart, setIsStart] = useState('2020-01-01')
  const [isEnd, setIsEnd] = useState('2024-12-31')
  const [engine, setEngine] = useState<'sim' | 'zipline'>('sim')

  const mut = useMutation({
    mutationFn: (body: RunCreateRequest) => createRun(body),
    onSuccess: (res) => {
      const id = res.data?.run_id
      if (id) navigate(`/research/runs/${encodeURIComponent(id)}`)
      else navigate('/research/runs')
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    mut.mutate({
      hypothesis: hypothesis.trim(),
      preset: preset.trim(),
      stocks: stocks.split(',').map((s) => s.trim()).filter(Boolean),
      is_start: isStart,
      is_end: isEnd,
      engine,
    })
  }

  const err = mut.error instanceof ApiError ? mut.error : null

  return (
    <form onSubmit={submit}>
      <PageHeader title="New Run 設定" route="/research/runs/new" subtitle="預先註冊假設 → 參數化 → 成本與期間" />

      {/* hypothesis（預先註冊） */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <label className={label}>Hypothesis · 單一論點（必填，提交後鎖定）</label>
        <textarea
          required
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          rows={2}
          className={field}
          placeholder="例：N-of-4 進場放寬至 3-of-4 能在 IS 達 Sharpe ≥ 1.0 且不過擬合"
        />
      </section>

      {/* parameters（精簡版：preset + stocks） */}
      <section className="mb-3 grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        <div>
          <label className={label}>Preset（StrategyConfig v2 / v3 …）</label>
          <input required value={preset} onChange={(e) => setPreset(e.target.value)} className={field} />
        </div>
        <div>
          <label className={label}>Stocks（逗號分隔，至少 1）</label>
          <input required value={stocks} onChange={(e) => setStocks(e.target.value)} className={`${field} font-mono`} />
        </div>
      </section>
      <div className="mb-3">
        <PendingNote label="完整 13 參數 / range-step / universe filter（待後端擴充 RunConfig）" />
      </div>

      {/* cost_engine */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <label className={label}>Engine</label>
        <div className="flex gap-2">
          {(['sim', 'zipline'] as const).map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => setEngine(e)}
              className={`rounded-md border px-3 py-1 text-sm ${
                engine === e ? 'border-text text-text' : 'border-border text-text-secondary'
              }`}
            >
              {e}
            </button>
          ))}
        </div>
        <div className="mt-3">
          <PendingNote label="成本攤平（手續費/滑點/漲跌停/T+2）（待後端擴充）" />
        </div>
      </section>

      {/* period（IS 區間；OOS 鎖死待後端 sealed vault） */}
      <section className="mb-3 grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        <div>
          <label className={label}>IS Start</label>
          <input required type="date" value={isStart} onChange={(e) => setIsStart(e.target.value)} className={`${field} font-mono`} />
        </div>
        <div>
          <label className={label}>IS End</label>
          <input required type="date" value={isEnd} onChange={(e) => setIsEnd(e.target.value)} className={`${field} font-mono`} />
        </div>
      </section>

      {/* submit_bar */}
      <div className="sticky bottom-0 flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3">
        {err && (
          <span className="text-sm text-error">
            {err.code}：{err.message}
          </span>
        )}
        <button
          type="submit"
          disabled={mut.isPending}
          className="ml-auto rounded-pill bg-text px-5 py-2 text-sm font-medium text-base hover:opacity-90 disabled:opacity-50"
        >
          {mut.isPending ? '提交中…' : '提交回測'}
        </button>
      </div>
    </form>
  )
}
