import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TradeReviewPage } from './TradeReviewPage'

afterEach(() => vi.unstubAllGlobals())

function stubFetch(opts: { empty?: boolean } = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const isTrades = String(url).endsWith('/trades')
      const body = opts.empty
        ? { success: true, data: isTrades ? { run_id: 'r1', trades: [] } : { run_id: 'r1', equity: [], drawdown: [] }, error: null, meta: { data_source: 'pending' } }
        : {
            success: true,
            data: isTrades
              ? { run_id: 'r1', trades: [{ ret: 0.05, hold: 7, entry_structure: 2 }, { ret: -0.02, hold: 3, entry_structure: 1 }] }
              : { run_id: 'r1', equity: [1.0, 1.03, 1.01], drawdown: [0.0, 0.0, -0.019] },
            error: null,
            meta: {},
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

  it('shows empty state when run has no persisted series', async () => {
    stubFetch({ empty: true })
    renderAt()
    await waitFor(() => expect(screen.getByText(/尚無逐筆交易紀錄/)).toBeInTheDocument())
  })
})
