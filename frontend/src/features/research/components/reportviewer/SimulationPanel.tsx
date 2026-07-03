/*
 * What-if 模擬面板（Goal 8）—— Report Viewer 內的「研究沙盤」。
 *
 * slider（成本乘數 / 滑價 bps / capacity）+ 選填數字（停損 / 停利 %）→ 按「執行模擬」才打
 * POST /research/simulate（不 keystroke 打 API、結果不進 react-query 快取——本地 state 即算即棄）。
 * 呈現 before/after 指標對照（Δ 有色、方向依指標好壞含義）+ affected trades 數 + 顯眼
 * 「研究沙盤——不影響正式判決」標示 + branch suggestion 卡（fork 按鈕 disabled，待 Goal 9）。
 *
 * 誠實降級：panel 策略無 per-trade pnl → 停損/停利 not_available（trade_metrics.available=false
 * + per_param reason），面板照實顯示原因，不留無說明佔位（契約 §13.2 / rule #6）。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { ApiError } from '@/services/http'
import type { DataSource } from '../../api/reportViewer'
import {
  deltaTone,
  fmtSimDelta,
  fmtSimValue,
  PORTFOLIO_METRIC_KEYS,
  runSimulation,
  TRADE_METRIC_KEYS,
  type MetricSpace,
  type SimulationRequest,
  type SimulationResult,
} from '../../api/simulation'

const TONE_CLASS: Record<'gain' | 'loss' | 'neutral', string> = {
  gain: 'text-gain',
  loss: 'text-loss-aaa',
  neutral: 'text-text-secondary',
}

/** 面板本地表單狀態（SL/TP 以百分比輸入字串持有，空字串=停用）。 */
interface FormState {
  costMultiplier: number
  slippageBps: number
  capacityScale: number
  stopLossPct: string
  takeProfitPct: string
}

const DEFAULTS: FormState = {
  costMultiplier: 1.0,
  slippageBps: 0,
  capacityScale: 1.0,
  stopLossPct: '',
  takeProfitPct: '',
}

/** 百分比輸入字串 → fraction（空/非數 → null）。 */
function pctToFraction(s: string): number | null {
  if (s.trim() === '') return null
  const v = Number(s)
  return Number.isFinite(v) && v > 0 ? v / 100 : null
}

function MetricSpaceTable({
  title,
  space,
  keys,
  t,
}: {
  title: string
  space: MetricSpace
  keys: readonly string[]
  t: (k: string, o?: Record<string, unknown>) => string
}) {
  if (!space.available)
    return (
      <div>
        <h4 className="text-xs font-medium text-text-muted">{title}</h4>
        <p
          data-testid={`sim-space-unavailable-${space.space}`}
          className="mt-1 rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-xs text-text-muted"
        >
          <span aria-hidden>⊘ </span>
          {t('reportViewer.simulation.notAvailable')}：{space.reason}
        </p>
      </div>
    )
  return (
    <div className="overflow-x-auto">
      <h4 className="mb-1 text-xs font-medium text-text-muted">{title}</h4>
      <table className="w-full min-w-[380px] text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-muted">
            <th className="py-1 pr-3 font-medium">{t('reportViewer.simulation.metricCol')}</th>
            <th className="py-1 pr-3 text-right font-medium">{t('reportViewer.simulation.beforeCol')}</th>
            <th className="py-1 pr-3 text-right font-medium">{t('reportViewer.simulation.afterCol')}</th>
            <th className="py-1 text-right font-medium">{t('reportViewer.simulation.deltaCol')}</th>
          </tr>
        </thead>
        <tbody>
          {keys.map((k) => {
            const delta = space.deltas?.[k]
            const tone = deltaTone(k, delta)
            return (
              <tr key={k} className="border-b border-border/40">
                <td className="py-1 pr-3 text-text">{t(`reportViewer.simulation.metric.${k}`, { defaultValue: k })}</td>
                <td className="py-1 pr-3 text-right font-mono tabular text-text-secondary">
                  {fmtSimValue(k, space.before?.[k])}
                </td>
                <td className="py-1 pr-3 text-right font-mono tabular text-text">{fmtSimValue(k, space.after?.[k])}</td>
                <td className={`py-1 text-right font-mono tabular ${TONE_CLASS[tone]}`} data-testid={`sim-delta-${k}`}>
                  {fmtSimDelta(k, delta)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function SimulationPanel({ runId, source }: { runId: string; source: DataSource }) {
  const { t } = useTranslation('research')
  const [form, setForm] = useState<FormState>(DEFAULTS)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isFixture = source === 'fixture'

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }))

  const execute = () => {
    setError(null)
    setRunning(true)
    const req: SimulationRequest = {
      run_id: runId,
      cost_multiplier: form.costMultiplier,
      slippage_bps: form.slippageBps,
      capacity_scale: form.capacityScale,
      stop_loss_pct: pctToFraction(form.stopLossPct),
      take_profit_pct: pctToFraction(form.takeProfitPct),
    }
    // 刻意不經 react-query：即算即棄的沙盤結果不入快取，避免過期參數殘留污染 Report Viewer。
    runSimulation(req)
      .then((r) => setResult(r))
      .catch((e) => setError(e instanceof ApiError ? e.message : t('reportViewer.simulation.runError')))
      .finally(() => setRunning(false))
  }

  return (
    <section className="mt-4 rounded-lg border border-border bg-surface p-4" data-testid="simulation-panel">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-medium text-text">{t('reportViewer.simulation.title')}</h3>
        {/* 顯眼「研究沙盤」標示——不影響正式判決 */}
        <StatusBadge tone="warning">
          <span aria-hidden>◆</span>
          {t('reportViewer.simulation.researchOnly')}
        </StatusBadge>
      </div>
      <p className="mt-1 text-xs text-text-muted">{t('reportViewer.simulation.subtitle')}</p>

      {/* 控制列 */}
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <SliderRow
          label={t('reportViewer.simulation.costMultiplier')}
          value={form.costMultiplier}
          min={0.5}
          max={3}
          step={0.1}
          suffix="×"
          testid="sim-cost-multiplier"
          onChange={(v) => set('costMultiplier', v)}
        />
        <SliderRow
          label={t('reportViewer.simulation.slippageBps')}
          value={form.slippageBps}
          min={0}
          max={50}
          step={1}
          suffix=" bps"
          testid="sim-slippage-bps"
          onChange={(v) => set('slippageBps', v)}
        />
        <SliderRow
          label={t('reportViewer.simulation.capacityScale')}
          value={form.capacityScale}
          min={0.1}
          max={3}
          step={0.1}
          suffix="×"
          testid="sim-capacity-scale"
          onChange={(v) => set('capacityScale', v)}
        />
        <NumberRow
          label={t('reportViewer.simulation.stopLossPct')}
          value={form.stopLossPct}
          placeholder={t('reportViewer.simulation.optionalPct')}
          testid="sim-stop-loss"
          onChange={(v) => set('stopLossPct', v)}
        />
        <NumberRow
          label={t('reportViewer.simulation.takeProfitPct')}
          value={form.takeProfitPct}
          placeholder={t('reportViewer.simulation.optionalPct')}
          testid="sim-take-profit"
          onChange={(v) => set('takeProfitPct', v)}
        />
        <div className="flex items-end">
          <button
            type="button"
            data-testid="sim-run"
            onClick={execute}
            disabled={running || isFixture}
            title={isFixture ? t('reportViewer.simulation.fixtureHint') : undefined}
            className="w-full rounded-md bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90 disabled:opacity-40"
          >
            {running ? t('reportViewer.simulation.running') : t('reportViewer.simulation.run')}
          </button>
        </div>
      </div>

      {isFixture && (
        <p className="mt-2 text-xs text-text-muted">
          <span aria-hidden>◆ </span>
          {t('reportViewer.simulation.fixtureHint')}
        </p>
      )}
      {error && (
        <p className="mt-2 text-xs text-error" data-testid="sim-error">
          {t('reportViewer.simulation.error', { detail: error })}
        </p>
      )}

      {/* 結果 */}
      {result && (
        <div className="mt-4 space-y-4" data-testid="sim-result">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <StatusBadge tone="muted">
              {t('reportViewer.simulation.affected', { n: result.affected_trades_count })}
            </StatusBadge>
          </div>

          <MetricSpaceTable
            title={t('reportViewer.simulation.portfolioSpace')}
            space={result.portfolio_metrics}
            keys={PORTFOLIO_METRIC_KEYS}
            t={t}
          />
          <MetricSpaceTable
            title={t('reportViewer.simulation.tradeSpace')}
            space={result.trade_metrics}
            keys={TRADE_METRIC_KEYS}
            t={t}
          />

          {result.branch_suggestion && (
            <div
              className="rounded-lg border border-border bg-base p-3"
              data-testid="sim-branch-suggestion"
            >
              <h4 className="text-xs font-medium text-text">{t('reportViewer.simulation.branchTitle')}</h4>
              <p className="mt-1 text-xs text-text-muted">{result.branch_suggestion.description}</p>
              <ul className="mt-2 space-y-0.5 text-xs text-text-secondary">
                {result.branch_suggestion.config_delta.map((d) => (
                  <li key={d.key} className="font-mono tabular">
                    {d.key}: {d.from ?? '—'} → {d.to}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                data-testid="sim-fork"
                disabled
                title={t('reportViewer.simulation.forkDisabled')}
                className="mt-2 rounded-md border border-border px-3 py-1 text-xs text-text-muted disabled:opacity-50"
              >
                {t('reportViewer.simulation.fork')}
              </button>
              <span className="ml-2 text-[11px] text-text-muted">{t('reportViewer.simulation.forkDisabled')}</span>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  suffix,
  testid,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  suffix: string
  testid: string
  onChange: (v: number) => void
}) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between text-xs text-text-muted">
        <span>{label}</span>
        <span className="font-mono tabular text-text-secondary">
          {value}
          {suffix}
        </span>
      </span>
      <input
        type="range"
        data-testid={testid}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-text"
      />
    </label>
  )
}

function NumberRow({
  label,
  value,
  placeholder,
  testid,
  onChange,
}: {
  label: string
  value: string
  placeholder: string
  testid: string
  onChange: (v: string) => void
}) {
  return (
    <label className="block">
      <span className="text-xs text-text-muted">{label}</span>
      <input
        type="number"
        inputMode="decimal"
        data-testid={testid}
        value={value}
        placeholder={placeholder}
        min={0}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-border bg-base px-2 py-1 text-sm text-text"
      />
    </label>
  )
}
