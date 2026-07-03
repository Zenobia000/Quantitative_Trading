import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { StrategyHubListPage } from './StrategyHubListPage'
import type { WatchRow } from '@/features/monitor/hooks/useWatch'
import type { Candidate } from '../api/candidates'

/** Minimal but contract-shaped WatchRow (mirrors GET /monitor/watch enrichment). */
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

/** Contract-shaped Candidate (mirrors GET /research/candidates enrichment). */
function candidate(over: Partial<Candidate> = {}): Candidate {
  return {
    candidate_id: 'cand_four_layer',
    strategy: 'four_layer',
    hypothesis: 'Relaxed N-of-4 breakout keeps Sharpe ≥ 1.0 out-of-sample',
    created_at: '2026-06-14T10:00:00+08:00',
    state: 'promising',
    latest_evaluation_id: 'eval_four_layer_quick_triage',
    latest_profile: 'quick_triage',
    latest_label: 'Promising',
    latest_truth_verdict: null,
    live_oos_recommendation: 'eligible',
    scorecard_summary: {
      profitability: 'pass',
      risk: 'pass',
      risk_adjusted: 'warn',
      win_rate: 'not_available',
      liquidity: 'pass',
    },
    headline: {
      sharpe: 1.3,
      oos_holdout_sharpe: 1.1,
      cagr: 0.2,
      max_drawdown: 0.15,
      dsr: 0.9,
      trades: 50,
      avg_turnover: 0.5,
      survivorship_clean: true,
    },
    report_pack_ref: 'reports/research_runs/abc123/manifest.json',
    next_action: 'Keep as research asset; consider live OOS.',
    decisions: [],
    ...over,
  }
}

/** URL-aware fetch mock: routes /strategies, /runs, /monitor/watch, /research/candidates. */
function mockApis(sets: {
  strategies?: unknown[]
  runs?: unknown[]
  watch?: unknown[]
  candidates?: unknown[]
}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const data =
        path === '/strategies'
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

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/research/strategies']}>
        <StrategyHubListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('StrategyHubListPage', () => {
  it('roster card → title + name + latest gate + watch badge + run count', async () => {
    mockApis({
      strategies: [
        { name: 'four_layer', title: 'Four-Layer Breakout', description: 'N-of-4 breakout', config_schema: {} },
      ],
      runs: [{ run_id: 'r1', strategy: 'four_layer', gate_status: 'PASS', metrics: { sharpe: 1.2 } }],
      watch: [watchRow()],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Four-Layer Breakout')).toBeInTheDocument())
    expect(screen.getByText('four_layer')).toBeInTheDocument()
    // latest run gate_status PASS → EnumBadge localized '通過'
    expect(screen.getByText('通過')).toBeInTheDocument()
    // enrolled in watch → watchState 'active' localized '觀察中'
    expect(screen.getByText('觀察中')).toBeInTheDocument()
    expect(screen.getByText('1 runs')).toBeInTheDocument()
    // per-card Evaluate CTA present
    expect(screen.getByText('評估')).toBeInTheDocument()
  })

  it('candidate enrichment → state badge + scorecard lights + hypothesis + profile', async () => {
    mockApis({
      strategies: [
        { name: 'four_layer', title: 'Four-Layer Breakout', description: 'N-of-4 breakout', config_schema: {} },
      ],
      runs: [{ run_id: 'r1', strategy: 'four_layer', gate_status: 'PASS', metrics: { sharpe: 1.2 } }],
      watch: [],
      candidates: [candidate()],
    })
    renderPage()
    // candidate state 'promising' → localized '有潛力'
    await waitFor(() => expect(screen.getByText('有潛力')).toBeInTheDocument())
    // hypothesis line comes from the candidate (highest-fidelity source)
    expect(
      screen.getByText('Relaxed N-of-4 breakout keeps Sharpe ≥ 1.0 out-of-sample'),
    ).toBeInTheDocument()
    // latest profile surfaced
    expect(screen.getByText('quick_triage')).toBeInTheDocument()
    // five scorecard lights render their dimension short-labels (dual-encoded)
    expect(screen.getByText('風報')).toBeInTheDocument()
  })

  it('strategy with zero runs & no candidate → honest noRuns + notEvaluated + 0 count', async () => {
    mockApis({
      strategies: [{ name: 'inst_flow', title: 'Institutional Flow', description: '', config_schema: {} }],
      runs: [],
      watch: [],
      candidates: [],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Institutional Flow')).toBeInTheDocument())
    expect(screen.getByText('尚無 run')).toBeInTheDocument()
    expect(screen.getByText('尚未評估')).toBeInTheDocument()
    expect(screen.getByText('0 runs')).toBeInTheDocument()
  })

  it('empty catalog → FirstRunEmptyState', async () => {
    mockApis({ strategies: [], runs: [], watch: [], candidates: [] })
    renderPage()
    await waitFor(() => expect(screen.getByText('尚無策略，從第一次回測開始')).toBeInTheDocument())
  })
})
