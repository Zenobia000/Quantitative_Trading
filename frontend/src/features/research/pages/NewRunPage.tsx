/*
 * New Run 設定（/research/runs/new）。Research terminal 的 hypothesis registration 入口。
 * 接真實 POST /runs（shipped；RunCreateRequest 型別取自 OpenAPI）。提交成功 → 跳 Run Report。
 * ADR-028：body 為 strategy（已註冊策略名，取自 GET /strategies 型錄）+ params（策略參數 dict），
 * 取代舊 preset 欄位。完整 range-step / OOS 鎖死待後端擴充 RunConfig（companion 後端 goal）。
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createRun, type RunCreateRequest } from '../api/createRun'
import { useStrategyRegistry } from '../hooks/useStrategyRegistry'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { useErrorText } from '@/i18n/useErrorText'

const field = 'w-full rounded-md border border-border bg-input px-3 py-1.5 text-sm'
const label = 'mb-1 block text-xs text-text-secondary'

export function NewRunPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const [sp] = useSearchParams()
  const registry = useStrategyRegistry()
  const strategies = Array.isArray(registry.data?.data) ? registry.data.data : []

  const [hypothesis, setHypothesis] = useState('')
  // 策略中心「New Run」以 ?strategy= 深連結預填此欄（refresh-safe）；未帶則預設 four_layer。
  const [strategy, setStrategy] = useState(sp.get('strategy') ?? 'four_layer')
  const [paramsText, setParamsText] = useState('{}')
  const [stocks, setStocks] = useState('2330,2454')
  const [isStart, setIsStart] = useState('2020-01-01')
  const [isEnd, setIsEnd] = useState('2024-12-31')
  const [engine, setEngine] = useState<'sim' | 'zipline'>('sim')
  const [paramsError, setParamsError] = useState<string | null>(null)
  // 進階（raw JSON params）預設收合 —— guided 欄位先行，params 為 opt-in 逃生艙（PD-01）。
  const [advOpen, setAdvOpen] = useState(false)

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
          setParamsError(t('newRun.params.errorObject'))
          setAdvOpen(true)
          return
        }
        params = parsed as Record<string, unknown>
      } catch {
        setParamsError(t('newRun.params.errorParse'))
        setAdvOpen(true)
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

  return (
    <form onSubmit={submit}>
      <PageHeader title={t('newRun.title')} route="/research/runs/new" subtitle={t('newRun.subtitle')} />

      {/* hypothesis（預先註冊） */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <label className={label}>{t('newRun.hypothesis.label')}</label>
        <textarea
          required
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          rows={2}
          className={field}
          placeholder={t('newRun.hypothesis.placeholder')}
        />
      </section>

      {/* parameters（strategy + params + stocks） */}
      <section className="mb-3 grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        <div>
          <label className={label}>{t('newRun.strategy.label')}</label>
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
          <label className={label}>{t('newRun.stocks.label')}</label>
          <input required value={stocks} onChange={(e) => setStocks(e.target.value)} className={`${field} font-mono`} />
        </div>
        <details
          open={advOpen}
          onToggle={(e) => setAdvOpen((e.currentTarget as HTMLDetailsElement).open)}
          className="rounded-md border border-border/60 sm:col-span-2"
        >
          <summary className="cursor-pointer select-none px-3 py-2 text-xs text-text-secondary marker:text-text-muted">
            {t('newRun.params.summary')}
          </summary>
          <div className="px-3 pb-3">
            <textarea
              value={paramsText}
              onChange={(e) => setParamsText(e.target.value)}
              rows={2}
              className={`${field} font-mono`}
              placeholder='{"box_period": 60, "entry_confirm_days": 2}'
            />
            {paramsError && <p className="mt-1 text-xs text-error">{paramsError}</p>}
          </div>
        </details>
      </section>
      <div className="mb-3">
        <PendingNote label={t('newRun.pending.paramForm')} />
      </div>

      {/* cost_engine */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <label className={label}>{t('newRun.engine.label')}</label>
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
          <PendingNote label={t('newRun.pending.cost')} />
        </div>
      </section>

      {/* period（IS 區間；OOS 鎖死待後端 sealed vault） */}
      <section className="mb-3 grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2">
        <div>
          <label className={label}>{t('newRun.period.isStart')}</label>
          <input required type="date" value={isStart} onChange={(e) => setIsStart(e.target.value)} className={`${field} font-mono`} />
        </div>
        <div>
          <label className={label}>{t('newRun.period.isEnd')}</label>
          <input required type="date" value={isEnd} onChange={(e) => setIsEnd(e.target.value)} className={`${field} font-mono`} />
        </div>
      </section>

      {/* submit_bar */}
      <div className="sticky bottom-0 flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3">
        {mut.isError && <span className="text-sm text-error">{errText(mut.error)}</span>}
        <button
          type="submit"
          disabled={mut.isPending}
          className="ml-auto rounded-pill bg-text px-5 py-2 text-sm font-medium text-base hover:opacity-90 disabled:opacity-50"
        >
          {mut.isPending ? t('newRun.submit.submitting') : t('newRun.submit.label')}
        </button>
      </div>
    </form>
  )
}
