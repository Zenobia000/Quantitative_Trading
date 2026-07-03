import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { SignalsPage } from './SignalsPage'

function mock(data: unknown, meta: unknown = { ttl: 30, data_source: 'timescaledb' }) {
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
        <SignalsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

describe('SignalsPage', () => {
  it('telemetry → signal rows', async () => {
    mock([{ signal_time: '2023-01-03T00:00:00', strategy_id: 'inst_flow', stock_id: '2454', action: 'buy', priority: 2, submitted: true }])
    renderPage()
    await waitFor(() => expect(screen.getAllByText('2454').length).toBeGreaterThan(0))
  })
  it('pending → PendingNote', async () => {
    mock([], { data_source: 'pending' })
    renderPage()
    await waitFor(() => expect(screen.getAllByText(/待紙上交易遙測/).length).toBeGreaterThan(0))
  })
})
