import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TradeReviewPage } from './TradeReviewPage'

// CandlestickChart pulls in lightweight-charts (canvas) — mock it so the page
// test never touches the canvas lib; the chart lib has its own smoke test.
vi.mock('../components/CandlestickChart', () => ({
  CandlestickChart: ({ candles, markers }: { candles: unknown[]; markers: unknown[] }) => (
    <div data-testid="chart-mock">{`candles:${candles.length} markers:${markers.length}`}</div>
  ),
}))

afterEach(() => vi.unstubAllGlobals())

interface StubOpts {
  emptySeries?: boolean
  candlesPending?: boolean
  symbols?: string[]
}

function stubFetch(opts: StubOpts = {}) {
  const symbols = opts.symbols ?? ['2330']
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = String(url)
      let body: unknown
      if (u.includes('/candles')) {
        body = opts.candlesPending
          ? { success: true, data: { run_id: 'r1', symbol: symbols[0], symbols, candles: [], markers: [] }, error: null, meta: { data_source: 'pending' } }
          : {
              success: true,
              data: {
                run_id: 'r1',
                symbol: symbols[0],
                symbols,
                candles: [{ time: '2020-01-01', open: 10, high: 12, low: 9, close: 11, volume: 100 }],
                markers: [{ time: '2020-01-01', kind: 'entry', price: 10 }],
              },
              error: null,
              meta: {},
            }
      } else if (u.endsWith('/trades')) {
        body = opts.emptySeries
          ? { success: true, data: { run_id: 'r1', trades: [] }, error: null, meta: { data_source: 'pending' } }
          : { success: true, data: { run_id: 'r1', trades: [{ ret: 0.05, hold: 7, entry_structure: 2 }, { ret: -0.02, hold: 3, entry_structure: 1 }] }, error: null, meta: {} }
      } else {
        // /equity
        body = opts.emptySeries
          ? { success: true, data: { run_id: 'r1', equity: [], drawdown: [] }, error: null, meta: { data_source: 'pending' } }
          : { success: true, data: { run_id: 'r1', equity: [1.0, 1.03, 1.01], drawdown: [0.0, 0.0, -0.019] }, error: null, meta: {} }
      }
      return { status: 200, json: async () => body }
    }) as unknown as typeof fetch,
  )
}

function renderAt(path = '/research/runs/r1/trades') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/research/runs/:id/trades" element={<TradeReviewPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TradeReviewPage', () => {
  it('renders trades table + win-rate + equity summary', async () => {
    stubFetch()
    renderAt()
    await waitFor(() => expect(screen.getByText('5.00%')).toBeInTheDocument())
    expect(screen.getByText(/勝率 50.00%/)).toBeInTheDocument()
    expect(screen.getByText('1.0100')).toBeInTheDocument() // final equity
  })

  it('renders the candlestick chart with markers when candles present', async () => {
    stubFetch()
    renderAt()
    await waitFor(() =>
      expect(screen.getByTestId('chart-mock')).toHaveTextContent('candles:1 markers:1'),
    )
  })

  it('shows a symbol selector when the run has 2+ symbols', async () => {
    stubFetch({ symbols: ['2330', '2317'] })
    renderAt()
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
    expect(screen.getByRole('option', { name: '2317' })).toBeInTheDocument()
  })

  it('shows candlestick empty state when the symbol has no parquet', async () => {
    stubFetch({ candlesPending: true })
    renderAt()
    await waitFor(() => expect(screen.getByText(/此個股尚無 K 線資料/)).toBeInTheDocument())
  })

  it('shows empty state when run has no persisted series', async () => {
    stubFetch({ emptySeries: true })
    renderAt()
    await waitFor(() => expect(screen.getByText(/尚無逐筆交易紀錄/)).toBeInTheDocument())
  })
})
