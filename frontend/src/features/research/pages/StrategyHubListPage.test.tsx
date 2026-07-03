import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { StrategyHubListPage } from './StrategyHubListPage'
import type { WatchRow } from '@/features/monitor/hooks/useWatch'

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

/** URL-aware fetch mock: routes /strategies, /runs, /monitor/watch to their datasets. */
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
  })

  it('strategy with zero runs → honest noRuns + 0 count (registry-driven roster)', async () => {
    mockApis({
      strategies: [{ name: 'inst_flow', title: 'Institutional Flow', description: '', config_schema: {} }],
      runs: [],
      watch: [],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Institutional Flow')).toBeInTheDocument())
    expect(screen.getByText('尚無 run')).toBeInTheDocument()
    expect(screen.getByText('0 runs')).toBeInTheDocument()
  })

  it('empty catalog → FirstRunEmptyState', async () => {
    mockApis({ strategies: [], runs: [], watch: [] })
    renderPage()
    await waitFor(() => expect(screen.getByText('尚無策略，從第一次回測開始')).toBeInTheDocument())
  })
})
