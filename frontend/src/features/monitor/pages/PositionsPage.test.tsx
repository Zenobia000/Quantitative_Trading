import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { PositionsPage } from './PositionsPage'

function mock(data: unknown, meta: unknown = { ttl: 60, data_source: 'timescaledb' }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ status: 200, json: async () => ({ success: true, data, error: null, meta }) })) as unknown as typeof fetch,
  )
}
function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PositionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

describe('PositionsPage', () => {
  it('telemetry → position rows', async () => {
    mock([{ stock_id: '2330', quantity: 100, entry_price: 600, stop_loss: 576, opened_at: '2023-01-03T00:00:00', strategy_id: 'inst_flow' }])
    renderPage()
    await waitFor(() => expect(screen.getByText('2330')).toBeInTheDocument())
    expect(screen.getByText('inst_flow')).toBeInTheDocument()
  })
  it('pending → PendingNote', async () => {
    mock([], { data_source: 'pending_m4' })
    renderPage()
    await waitFor(() => expect(screen.getByText(/待紙上交易遙測/)).toBeInTheDocument())
  })
})
