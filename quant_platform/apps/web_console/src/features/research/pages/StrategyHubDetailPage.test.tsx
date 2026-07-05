import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { StrategyHubDetailPage } from './StrategyHubDetailPage'
import type { WatchRow } from '@/features/monitor/hooks/useWatch'
import type { Candidate } from '../api/candidates'

function watchRow(over: Partial<WatchRow> = {}): WatchRow {
  return {
    strategy: 'four_layer',
    status: 'active',
    enrolled_on: '2026-06-01',
    verdict_dsr: 0.91,
    observed_trading_days: 22,
    nominal_trading_days: 60,
    expiry_date: '2026-08-30',
    days_remaining: 38,
    timer_health: 'ok',
    last_session_date: '2026-07-03',
    last_session_at: '2026-07-03T14:32:05+08:00',
    last_trading_day: '2026-07-03',
    sessions: [],
    ...over,
  }
}

function candidate(over: Partial<Candidate> = {}): Candidate {
  return {
    candidate_id: 'cand_four_layer',
    strategy: 'four_layer',
    hypothesis: 'Foreign net-buy flow predicts forward return',
    created_at: '2026-06-14T10:00:00+08:00',
    state: 'weak',
    latest_evaluation_id: 'eval_four_layer_deployment_strict',
    latest_profile: 'deployment_strict',
    latest_label: 'Weak',
    latest_truth_verdict: 'PAPER_WATCH',
    live_oos_recommendation: 'eligible',
    scorecard_summary: {
      profitability: 'warn',
      risk: 'pass',
      risk_adjusted: 'warn',
      win_rate: 'not_available',
      liquidity: 'warn',
    },
    headline: {
      sharpe: 1.02,
      oos_holdout_sharpe: 0.89,
      cagr: 0.16,
      max_drawdown: 0.27,
      dsr: 0.9,
      trades: 60,
      avg_turnover: 0.83,
      survivorship_clean: true,
    },
    report_pack_ref: 'reports/research_runs/a1b9c3d4/manifest.json',
    next_action: 'Collect 3-month zero-capital live OOS, then re-evaluate DSR.',
    decisions: [
      {
        decision_id: 'dec_0002',
        candidate_id: 'cand_four_layer',
        at: '2026-07-02T18:45:00+08:00',
        actor: 'operator',
        action: 'keep',
        from_state: 'triaged',
        to_state: 'weak',
        reason: 'DSR near-miss but OOS breadth 100%.',
        evaluation_ref: 'eval_four_layer_deployment_strict',
      },
    ],
    ...over,
  }
}

function mockApis(sets: {
  strategies?: unknown[]
  asset?: unknown
  runs?: unknown[]
  watch?: unknown[]
  candidates?: unknown[]
}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const data =
        path.endsWith('/asset')
          ? (sets.asset ?? {
              strategy: 'four_layer',
              package: 'backtest_platform.strategies.four_layer_resonance',
              package_path: 'src/backtest_platform/strategies/four_layer_resonance',
              files: [
                { path: 'strategy.py', role: 'alpha_logic', present: true },
                { path: 'runner.py', role: 'platform_adapter', present: true },
                { path: 'research_config.py', role: 'research_workflows', present: true },
              ],
              workflows: ['doe'],
              endpoints: {},
            })
          : path === '/strategies'
          ? (sets.strategies ?? [])
          : path === '/runs'
            ? (sets.runs ?? [])
            : path === '/monitor/watch'
              ? (sets.watch ?? [])
              : path === '/research/candidates'
                ? (sets.candidates ?? [])
                : []
      return { status: 200, json: async () => ({ success: true, data, error: null, meta: { ttl: 300 } }) }
    }) as unknown as typeof fetch,
  )
}

/** Deep-link the :name route so useParams resolves (refresh-safe URL is the point). */
function renderDetail(name: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/research/strategies/${name}`]}>
        <Routes>
          <Route path="/research/strategies/:name" element={<StrategyHubDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('StrategyHubDetailPage', () => {
  it('deep link :name → header title + verdict timeline (gate badge + run link)', async () => {
    mockApis({
      strategies: [
        { name: 'four_layer', title: 'Four-Layer Breakout', description: 'desc', config_schema: { properties: { box_period: {} } } },
      ],
      runs: [
        { run_id: 'run_new', strategy: 'four_layer', gate_status: 'PASS', hypothesis: 'h1', metrics: { sharpe: 1.3 } },
        { run_id: 'run_old', strategy: 'four_layer', gate_status: 'FAIL', hypothesis: 'h0', metrics: { sharpe: 0.4 } },
        { run_id: 'other', strategy: 'inst_flow', gate_status: 'PASS', metrics: { sharpe: 2.0 } },
      ],
      watch: [],
      candidates: [],
    })
    renderDetail('four_layer')
    await waitFor(() => expect(screen.getByText('Four-Layer Breakout')).toBeInTheDocument())
    // both of this strategy's runs listed; the other strategy's run excluded
    expect(screen.getByText('run_new')).toBeInTheDocument()
    expect(screen.getByText('run_old')).toBeInTheDocument()
    expect(screen.queryByText('other')).not.toBeInTheDocument()
    // gate badges present (PASS → 通過, FAIL → 未通過)
    expect(screen.getByText('通過')).toBeInTheDocument()
    expect(screen.getByText('未通過')).toBeInTheDocument()
    // config_model summary shows schema field
    expect(screen.getByText('box_period')).toBeInTheDocument()
    // research premise section present
    expect(screen.getByText('研究命題')).toBeInTheDocument()
    // strategy package descriptor present
    expect(screen.getByText('策略資料夾')).toBeInTheDocument()
    expect(screen.getByText('strategy.py')).toBeInTheDocument()
  })

  it('candidate present → lifecycle section (state + profile + next_action + decision trail)', async () => {
    mockApis({
      strategies: [{ name: 'four_layer', title: 'Four-Layer Breakout', description: 'desc', config_schema: {} }],
      runs: [{ run_id: 'run_new', strategy: 'four_layer', gate_status: 'PASS', metrics: {} }],
      watch: [],
      candidates: [candidate()],
    })
    renderDetail('four_layer')
    // lifecycle section header + candidate state 'weak' → '偏弱'
    await waitFor(() => expect(screen.getByText('候選生命週期')).toBeInTheDocument())
    expect(screen.getByText('偏弱')).toBeInTheDocument()
    expect(screen.getByText('deployment_strict')).toBeInTheDocument()
    expect(
      screen.getByText('Collect 3-month zero-capital live OOS, then re-evaluate DSR.'),
    ).toBeInTheDocument()
    // decision trail is collapsible → expand and see the recorded 'keep' action
    fireEvent.click(screen.getByText('決策軌跡（1）'))
    expect(screen.getByText('保留')).toBeInTheDocument()
    expect(screen.getByText('triaged→weak')).toBeInTheDocument()
  })

  it('no candidate → honest "not evaluated" empty guide', async () => {
    mockApis({
      strategies: [{ name: 'four_layer', title: 'Four-Layer Breakout', description: '', config_schema: {} }],
      runs: [{ run_id: 'run_new', strategy: 'four_layer', gate_status: 'PASS', metrics: {} }],
      watch: [],
      candidates: [],
    })
    renderDetail('four_layer')
    await waitFor(() => expect(screen.getByText('尚未評估')).toBeInTheDocument())
    // empty-state CTA ('立即評估') is distinct from the quick-entry primary ('評估此策略')
    expect(screen.getByText('立即評估')).toBeInTheDocument()
    expect(screen.getByText('評估此策略')).toBeInTheDocument()
  })

  it('enrolled → watch pod card (observed days N/~60 + expiry)', async () => {
    mockApis({
      strategies: [{ name: 'four_layer', title: 'Four-Layer Breakout', description: '', config_schema: {} }],
      runs: [{ run_id: 'run_new', strategy: 'four_layer', gate_status: 'PASS', metrics: {} }],
      watch: [watchRow({ observed_trading_days: 22, nominal_trading_days: 60 })],
      candidates: [],
    })
    renderDetail('four_layer')
    await waitFor(() => expect(screen.getByText('22/~60')).toBeInTheDocument())
    // watch pod header shows the localized watch-deck title + active badge
    expect(screen.getByText('觀察中')).toBeInTheDocument()
  })

  it('strategy with no runs → honest empty timeline', async () => {
    mockApis({
      strategies: [{ name: 'four_layer', title: 'Four-Layer Breakout', description: '', config_schema: {} }],
      runs: [],
      watch: [],
      candidates: [],
    })
    renderDetail('four_layer')
    await waitFor(() =>
      expect(screen.getByText('此策略尚無 run —— 從新建回測開始')).toBeInTheDocument(),
    )
  })
})
