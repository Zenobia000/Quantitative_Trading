/*
 * New Run 設定（/research/runs/new）。Research terminal 的 hypothesis registration 入口。
 * 接真實 POST /runs（shipped；RunCreateRequest 型別取自 OpenAPI）。提交成功 → 跳 Run Report。
 * ADR-028：body 為 strategy（已註冊策略名，取自 GET /strategies 型錄）+ params（策略參數 dict），
 * 取代舊 preset 欄位。完整 range-step / OOS 鎖死待後端擴充 RunConfig（companion 後端 goal）。
 */
import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createRun, type RunCreateRequest } from '../api/createRun'
import { submitDoeWorkflow } from '../api/registry'
import { useStrategyOptimizationSchema, useStrategyRegistry } from '../hooks/useStrategyRegistry'
import { useUniverses } from '@/features/system/hooks/useSystem'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { useErrorText } from '@/i18n/useErrorText'

/** 股票池選單哨兵值：系統預設 / 自訂 symbols（其餘為具名 universe id）。 */
const POOL_DEFAULT = '__default__'
const POOL_CUSTOM = '__custom__'

const field = 'w-full rounded-md border border-border bg-input px-3 py-1.5 text-sm'
const label = 'mb-1 block text-xs text-text-secondary'

type JsonSchema = Record<string, unknown>

interface ParamField {
  name: string
  type: string
  enumValues: unknown[]
  defaultValue: unknown
  description: string
}

function schemaProps(schema: Record<string, unknown> | undefined): Record<string, JsonSchema> {
  const props = schema?.properties
  return props && typeof props === 'object' ? (props as Record<string, JsonSchema>) : {}
}

function unwrapNullable(schema: JsonSchema): JsonSchema {
  const anyOf = schema.anyOf
  if (!Array.isArray(anyOf)) return schema
  const concrete = anyOf.find((s) => s && typeof s === 'object' && (s as JsonSchema).type !== 'null')
  return concrete ? { ...schema, ...(concrete as JsonSchema) } : schema
}

function enumValues(schema: JsonSchema): unknown[] {
  if (Array.isArray(schema.enum)) return schema.enum
  const anyOf = schema.anyOf
  if (!Array.isArray(anyOf)) return []
  const vals = anyOf
    .filter((s): s is JsonSchema => !!s && typeof s === 'object')
    .filter((s) => s.type !== 'null' && Object.prototype.hasOwnProperty.call(s, 'const'))
    .map((s) => s.const)
  return vals.length ? vals : []
}

function paramFields(schema: Record<string, unknown> | undefined): ParamField[] {
  return Object.entries(schemaProps(schema)).map(([name, raw]) => {
    const s = unwrapNullable(raw)
    const values = enumValues(raw)
    return {
      name,
      type: typeof s.type === 'string' ? s.type : values.length ? 'string' : 'string',
      enumValues: values,
      defaultValue: s.default,
      description: typeof s.description === 'string' ? s.description : '',
    }
  })
}

function parseParamValue(f: ParamField, raw: string | boolean): unknown {
  if (f.type === 'boolean') return Boolean(raw)
  if (f.type === 'integer') return raw === '' ? undefined : Math.trunc(Number(raw))
  if (f.type === 'number') return raw === '' ? undefined : Number(raw)
  return String(raw)
}

function splitGridValues(raw: string): unknown[] {
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const n = Number(s)
      return Number.isFinite(n) && s !== '' ? n : s
    })
}

function gridStats(grid: Record<string, string>): { axes: number; configs: number } {
  let axes = 0
  let configs = 1
  for (const raw of Object.values(grid)) {
    const n = splitGridValues(raw).length
    if (n > 0) {
      axes += 1
      configs *= n
    }
  }
  return { axes, configs: axes ? configs : 0 }
}

export function NewRunPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const [sp] = useSearchParams()
  const [hypothesis, setHypothesis] = useState('')
  // 策略中心「New Run」以 ?strategy= 深連結預填此欄（refresh-safe）；未帶則預設 four_layer。
  const [strategy, setStrategy] = useState(sp.get('strategy') ?? 'four_layer')
  const registry = useStrategyRegistry()
  const strategies = Array.isArray(registry.data?.data) ? registry.data.data : []
  const selectedInfo = strategies.find((s) => s.name === strategy)
  const fields = useMemo(() => paramFields(selectedInfo?.config_schema), [selectedInfo?.config_schema])
  const optQ = useStrategyOptimizationSchema(strategy)
  const optimization = optQ.data?.data?.optimization ?? null
  const universesQ = useUniverses()
  const universes = Array.isArray(universesQ.data?.data) ? universesQ.data.data : []

  const [paramsText, setParamsText] = useState('{}')
  const [guidedParams, setGuidedParams] = useState<Record<string, string | boolean>>({})
  const [gridText, setGridText] = useState<Record<string, string>>({})
  const [doeJob, setDoeJob] = useState<string | null>(null)
  // 股票池：預設用系統通用池（不必手打 symbols）；選具名池或「自訂」才需輸入。
  const [pool, setPool] = useState<string>(POOL_DEFAULT)
  const [stocks, setStocks] = useState('2330,2454')
  const [isStart, setIsStart] = useState('2020-01-01')
  const [isEnd, setIsEnd] = useState('2024-12-31')
  const [engine, setEngine] = useState<'sim' | 'zipline'>('sim')
  const [paramsError, setParamsError] = useState<string | null>(null)
  // 進階（raw JSON params）預設收合 —— guided 欄位先行，params 為 opt-in 逃生艙（PD-01）。
  const [advOpen, setAdvOpen] = useState(false)

  useEffect(() => {
    const grid = optimization?.grid ?? {}
    setGridText(Object.fromEntries(Object.entries(grid).map(([k, v]) => [k, Array.isArray(v) ? v.join(',') : ''])))
  }, [optimization])

  const mut = useMutation({
    mutationFn: (body: RunCreateRequest) => createRun(body),
    onSuccess: (res) => {
      const id = res.data?.run_id
      if (id) navigate(`/research/runs/${encodeURIComponent(id)}`)
      else navigate('/research/runs')
    },
  })

  const doeMut = useMutation({
    mutationFn: (grid: Record<string, unknown[]>) =>
      submitDoeWorkflow({ strategy: strategy.trim(), overrides: { grid } }),
    onSuccess: (res) => setDoeJob(res.data?.job_id ?? null),
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    // params 為選填 JSON dict；空白視為 {}，解析失敗則擋下（快速失敗，清楚訊息）
    let params: Record<string, unknown> = {}
    for (const f of fields) {
      if (!(f.name in guidedParams)) continue
      const parsed = parseParamValue(f, guidedParams[f.name])
      if (parsed !== undefined) params[f.name] = parsed
    }
    const raw = paramsText.trim()
    if (raw) {
      try {
        const parsed = JSON.parse(raw)
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
          setParamsError(t('newRun.params.errorObject'))
          setAdvOpen(true)
          return
        }
        params = { ...params, ...(parsed as Record<string, unknown>) }
      } catch {
        setParamsError(t('newRun.params.errorParse'))
        setAdvOpen(true)
        return
      }
    }
    setParamsError(null)
    // 股票池解析（ADR-007 精度序：自訂 stocks > 具名 universe > 系統預設）：
    //  - 自訂 → 送 stocks；具名池 → 送 universe（symbols 由後端解析）；預設 → 兩者皆不送。
    const body: RunCreateRequest = {
      hypothesis: hypothesis.trim(),
      strategy: strategy.trim(),
      params,
      is_start: isStart,
      is_end: isEnd,
      engine,
    }
    if (pool === POOL_CUSTOM) {
      body.stocks = stocks.split(',').map((s) => s.trim()).filter(Boolean)
    } else if (pool !== POOL_DEFAULT) {
      body.universe = pool
    }
    mut.mutate(body)
  }

  const submitDoe = () => {
    const grid: Record<string, unknown[]> = {}
    for (const [k, v] of Object.entries(gridText)) {
      const vals = splitGridValues(v)
      if (vals.length) grid[k] = vals
    }
    doeMut.mutate(grid)
  }

  const gridSummary = gridStats(gridText)

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
          <label className={label}>{t('newRun.pool.label')}</label>
          <select value={pool} onChange={(e) => setPool(e.target.value)} className={field}>
            <option value={POOL_DEFAULT}>{t('newRun.pool.systemDefault')}</option>
            {universes.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}（{u.symbols_count} {t('newRun.pool.stocksUnit')}）
              </option>
            ))}
            <option value={POOL_CUSTOM}>{t('newRun.pool.custom')}</option>
          </select>
          {/* 自訂才顯示 symbols 輸入；具名池/預設由後端解析 symbols */}
          {pool === POOL_CUSTOM && (
            <input
              required
              value={stocks}
              onChange={(e) => setStocks(e.target.value)}
              className={`${field} mt-2 font-mono`}
              placeholder="2330,2454"
            />
          )}
          {/* 產品面提示：預設池的通用邏輯與正式回測建議 */}
          {pool === POOL_DEFAULT && (
            <p className="mt-1 text-xs text-text-muted">{t('newRun.pool.defaultHint')}</p>
          )}
        </div>
        {fields.length > 0 && (
          <div className="sm:col-span-2">
            <div className="mb-2 text-xs text-text-muted">{t('newRun.params.guidedTitle')}</div>
            <div className="grid gap-3 sm:grid-cols-2">
              {fields.map((f) => {
                const current = guidedParams[f.name]
                const value = current ?? (f.defaultValue ?? '')
                return (
                  <label key={f.name} className="block">
                    <span className={label}>{f.name}</span>
                    {f.type === 'boolean' ? (
                      <input
                        type="checkbox"
                        checked={Boolean(value)}
                        onChange={(e) => setGuidedParams((p) => ({ ...p, [f.name]: e.target.checked }))}
                        className="h-4 w-4 accent-text"
                      />
                    ) : f.enumValues.length > 0 ? (
                      <select
                        value={String(value)}
                        onChange={(e) => setGuidedParams((p) => ({ ...p, [f.name]: e.target.value }))}
                        className={field}
                      >
                        {f.enumValues.map((v) => (
                          <option key={String(v)} value={String(v)}>
                            {String(v)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={f.type === 'integer' || f.type === 'number' ? 'number' : 'text'}
                        step={f.type === 'integer' ? 1 : 'any'}
                        value={String(value)}
                        onChange={(e) => setGuidedParams((p) => ({ ...p, [f.name]: e.target.value }))}
                        className={`${field} font-mono`}
                      />
                    )}
                    {f.description && <span className="mt-1 block text-xs text-text-muted">{f.description}</span>}
                  </label>
                )
              })}
            </div>
          </div>
        )}
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

      {/* DOE optimization grid（ADR-008）：讀 research_config.DOE.grid，可覆寫後送 workflow。 */}
      {optimization && (
        <section className="mb-3 rounded-lg border border-border bg-surface p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div>
              <div className="text-xs uppercase tracking-wide text-text-muted">{t('newRun.optimization.title')}</div>
              <div className="mt-0.5 text-xs text-text-secondary">
                {t('newRun.optimization.window', {
                  start: optimization.is_start,
                  end: optimization.is_end,
                  symbols: optimization.symbols_count,
                })}
              </div>
            </div>
            <span className="ml-auto font-mono text-xs text-text-muted">
              {t('newRun.optimization.gridStats', { axes: gridSummary.axes, configs: gridSummary.configs })}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {Object.entries(gridText).map(([k, v]) => (
              <label key={k} className="block">
                <span className={label}>{k}</span>
                <input
                  value={v}
                  onChange={(e) => setGridText((g) => ({ ...g, [k]: e.target.value }))}
                  className={`${field} font-mono`}
                />
              </label>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {doeMut.isError && <span className="text-sm text-error">{errText(doeMut.error)}</span>}
            {doeJob && <span className="font-mono text-xs text-text-muted">job {doeJob}</span>}
            <button
              type="button"
              onClick={submitDoe}
              disabled={doeMut.isPending}
              className="ml-auto rounded-md border border-info/60 px-3 py-1.5 text-sm text-info hover:bg-input disabled:opacity-50"
            >
              {doeMut.isPending ? t('newRun.optimization.submitting') : t('newRun.optimization.submit')}
            </button>
          </div>
        </section>
      )}

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
