import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { StrategyHubDetailPage } from './StrategyHubDetailPage'
import type { WatchRow } from '@/features/monitor/hooks/useWatch'

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

function mockApis(sets: { strategies?: unknown[]; runs?: unknown[]; watch?: unknown[] }) {
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
  })

  it('enrolled → watch pod card (observed days N/~60 + expiry)', async () => {
    mockApis({
      strategies: [{ name: 'four_layer', title: 'Four-Layer Breakout', description: '', config_schema: {} }],
      runs: [{ run_id: 'run_new', strategy: 'four_layer', gate_status: 'PASS', metrics: {} }],
      watch: [watchRow({ observed_trading_days: 22, nominal_trading_days: 60 })],
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
    })
    renderDetail('four_layer')
    await waitFor(() =>
      expect(screen.getByText('此策略尚無 run —— 從新建回測開始')).toBeInTheDocument(),
    )
  })
})
