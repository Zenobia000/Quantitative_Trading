/*
 * New Run 設定（/research/runs/new）。三源對齊 assembly + design.pen frame + page spec。
 * 接真實 POST /runs（shipped；RunCreateRequest 型別取自 OpenAPI）。提交成功 → 跳 Run Report。
 * ADR-028：body 為 strategy（已註冊策略名，取自 GET /strategies 型錄）+ params（策略參數 dict），
 * 取代舊 preset 欄位。完整 range-step / OOS 鎖死待後端擴充 RunConfig（companion 後端 goal）。
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { createRun, type RunCreateRequest } from '../api/createRun'
import { useStrategyRegistry } from '../hooks/useStrategyRegistry'
import { ApiError } from '@/services/http'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'

const field = 'w-full rounded-md border border-border bg-input px-3 py-1.5 text-sm'
const label = 'mb-1 block text-xs text-text-secondary'

export function NewRunPage() {
  const navigate = useNavigate()
  const registry = useStrategyRegistry()
  const strategies = Array.isArray(registry.data?.data) ? registry.data.data : []

  const [hypothesis, setHypothesis] = useState('')
  const [strategy, setStrategy] = useState('four_layer')
  const [paramsText, setParamsText] = useState('{}')
  const [stocks, setStocks] = useState('2330,2454')
  const [isStart, setIsStart] = useState('2020-01-01')
  const [isEnd, setIsEnd] = useState('2024-12-31')
  const [engine, setEngine] = useState<'sim' | 'zipline'>('sim')
  const [paramsError, setParamsError] = useState<string | null>(null)

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
    // params 為選填 JSON dict；空白視為 {}，解析失敗則擋下（快速失敗，清楚訊息）
    let params: Record<string, unknown> = {}
    const raw = paramsText.trim()
    if (raw) {
      try {
        const parsed = JSON.parse(raw)
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
          setParamsError('params 需為 JSON 物件（如 {"box_period": 60}）')
          return
        }
        params = parsed as Record<string, unknown>
      } catch {
        setParamsError('params JSON 格式錯誤')
        return
      }
    }
    setParamsError(null)
    mut.mutate({
      hypothesis: hypothesis.trim(),
      strategy: strategy.trim(),
      params,
      stocks: stocks.split(',').map((s) => s.trim()).filter(Boolean),
      is_start: isStart,
      is_end: isEnd,
      engine,
    })
  }

  const err = mut.error instanceof ApiError ? mut.error : null

  return (
    <form onSubmit={submit}>
      <PageHeader title="New Run 設定" route="/research/runs/new" subtitle="預先註冊假設 → 選策略 → 參數化 → 成本與期間" />

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

      {/* parameters（strategy + params + stocks） */}
      <section className="mb-3 grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        <div>
          <label className={label}>Strategy（已註冊策略名 · GET /strategies）</label>
          <input
            required
            list="strategy-options"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className={`${field} font-mono`}
            placeholder="four_layer"
          />
          <datalist id="strategy-options">
            {strategies.map((s) => (
              <option key={s.name} value={s.name}>
                {s.title}
              </option>
            ))}
          </datalist>
        </div>
        <div>
          <label className={label}>Stocks（逗號分隔，至少 1）</label>
          <input required value={stocks} onChange={(e) => setStocks(e.target.value)} className={`${field} font-mono`} />
        </div>
        <div className="sm:col-span-2">
          <label className={label}>Params（策略參數 JSON dict，選填；提交時驗證）</label>
          <textarea
            value={paramsText}
            onChange={(e) => setParamsText(e.target.value)}
            rows={2}
            className={`${field} font-mono`}
            placeholder='{"box_period": 60, "entry_confirm_days": 2}'
          />
          {paramsError && <p className="mt-1 text-xs text-error">{paramsError}</p>}
        </div>
      </section>
      <div className="mb-3">
        <PendingNote label="config_schema 驅動的參數表單 / range-step / universe filter（待後端擴充）" />
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
