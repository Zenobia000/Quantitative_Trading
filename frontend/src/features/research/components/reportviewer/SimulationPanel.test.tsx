/*
 * SimulationPanel（Goal 8）—— 研究沙盤面板單測。
 * 驗：研究沙盤標示、按「執行模擬」才打 API（不 keystroke）、before/after Δ 對照、affected 數、
 * branch suggestion fork 按鈕 disabled、panel 策略 trade_metrics not_available 誠實態、fixture 停用。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { SimulationPanel } from './SimulationPanel'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// 一份四層型結果（兩空間皆可用 + branch suggestion）。
const FOUR_LAYER_RESULT = {
  schema_version: '1.0',
  run_id: 'fl1',
  strategy: 'four_layer_resonance',
  research_only: true,
  applied_params: { run_id: 'fl1', cost_multiplier: 1.5, slippage_bps: 0, stop_loss_pct: 0.08, take_profit_pct: null, capacity_scale: 1 },
  portfolio_metrics: {
    available: true,
    reason: null,
    space: 'portfolio_equity',
    before: { total_return: 1.84, cagr: 0.12, sharpe: 0.94, sortino: 1.3, calmar: 0.42, max_drawdown: 0.288, ulcer_index: 0.12, volatility: 0.176 },
    after: { total_return: 1.61, cagr: 0.109, sharpe: 0.86, sortino: 1.19, calmar: 0.38, max_drawdown: 0.291, ulcer_index: 0.124, volatility: 0.176 },
    deltas: { total_return: -0.23, cagr: -0.011, sharpe: -0.08, sortino: -0.11, calmar: -0.04, max_drawdown: 0.003, ulcer_index: 0.004, volatility: 0 },
  },
  trade_metrics: {
    available: true,
    reason: null,
    space: 'trade_population',
    before: { n_trades: 214, win_rate: 0.48, avg_trade_return: 0.021, total_trade_return: 1.9, profit_factor: 1.44, avg_hold: 11.3 },
    after: { n_trades: 214, win_rate: 0.48, avg_trade_return: 0.019, total_trade_return: 1.74, profit_factor: 1.51, avg_hold: 11.3 },
    deltas: { n_trades: 0, win_rate: 0, avg_trade_return: -0.002, total_trade_return: -0.16, profit_factor: 0.07, avg_hold: 0 },
  },
  affected_trades_count: 37,
  per_param: [],
  branch_suggestion: {
    label: 'fork_as_branch_experiment',
    description: 'Fork this run into a branch experiment.',
    config_delta: [{ key: 'cost_multiplier', from: 1.0, to: 1.5, note: 'stress cost' }],
    actionable: false,
    actionable_reason: 'branch experiments land in Goal 9',
  },
  data_gaps: [],
}

// 一份 panel 型結果（trade_metrics not_available）。
const PANEL_RESULT = {
  ...FOUR_LAYER_RESULT,
  run_id: 'pn1',
  strategy: 'momentum',
  trade_metrics: {
    available: false,
    reason: 'strategy trades carry no per-trade return (panel rebalance count only) — stop-loss / take-profit what-if unavailable',
    space: 'trade_population',
    before: null,
    after: null,
    deltas: null,
  },
}

function stubSimulate(result: unknown): { posts: number } {
  const box = { posts: 0 }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes('/research/simulate') && (init?.method ?? 'GET') === 'POST') {
        box.posts += 1
        return { status: 200, json: async () => ({ success: true, data: result, error: null, meta: {} }) }
      }
      return { status: 404, json: async () => ({ success: false, data: null, error: { code: 'NOT_FOUND', message: 'nf' }, meta: {} }) }
    }) as unknown as typeof fetch,
  )
  return box
}

describe('SimulationPanel', () => {
  it('shows the research-only label and does not call the API on render (button-gated)', () => {
    const box = stubSimulate(FOUR_LAYER_RESULT)
    render(<SimulationPanel runId="fl1" source="api" />)
    expect(screen.getByText(/研究沙盤/)).toBeInTheDocument()
    // adjusting a slider must not fire the API (no keystroke calls).
    fireEvent.change(screen.getByTestId('sim-cost-multiplier'), { target: { value: '1.5' } })
    expect(box.posts).toBe(0)
  })

  it('runs the simulation on click and renders before/after deltas + affected count', async () => {
    const box = stubSimulate(FOUR_LAYER_RESULT)
    render(<SimulationPanel runId="fl1" source="api" />)
    fireEvent.click(screen.getByTestId('sim-run'))
    await waitFor(() => expect(screen.getByTestId('sim-result')).toBeInTheDocument())
    expect(box.posts).toBe(1)
    expect(screen.getByText(/受影響交易 37 筆/)).toBeInTheDocument()
    // total_return delta is negative → shown with a leading minus sign.
    expect(screen.getByTestId('sim-delta-total_return').textContent).toContain('-')
  })

  it('renders a disabled fork button with the Goal-9 note (branch suggestion, not applied)', async () => {
    stubSimulate(FOUR_LAYER_RESULT)
    render(<SimulationPanel runId="fl1" source="api" />)
    fireEvent.click(screen.getByTestId('sim-run'))
    await waitFor(() => expect(screen.getByTestId('sim-branch-suggestion')).toBeInTheDocument())
    const fork = screen.getByTestId('sim-fork')
    expect(fork).toBeDisabled()
    expect(screen.getAllByText(/待分支實驗（Goal 9）/).length).toBeGreaterThanOrEqual(1)
  })

  it('honestly shows trade-space not_available for a panel strategy (no per-trade pnl)', async () => {
    stubSimulate(PANEL_RESULT)
    render(<SimulationPanel runId="pn1" source="api" />)
    fireEvent.click(screen.getByTestId('sim-run'))
    await waitFor(() => expect(screen.getByTestId('sim-result')).toBeInTheDocument())
    const box = screen.getByTestId('sim-space-unavailable-trade_population')
    expect(within(box).getByText(/no per-trade return/)).toBeInTheDocument()
    // portfolio space still renders its table (cost/slippage/capacity feasible).
    expect(screen.getByTestId('sim-delta-total_return')).toBeInTheDocument()
  })

  it('disables the run button in fixture mode with a hint', () => {
    const box = stubSimulate(FOUR_LAYER_RESULT)
    render(<SimulationPanel runId="fl1" source="fixture" />)
    expect(screen.getByTestId('sim-run')).toBeDisabled()
    expect(box.posts).toBe(0)
  })
})
