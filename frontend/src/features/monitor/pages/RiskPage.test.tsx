import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { RiskPage } from './RiskPage'

function mock(data: unknown, meta: unknown) {
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
        <RiskPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

describe('RiskPage', () => {
  it('pending stub → PendingNote (current state, no fabrication)', async () => {
    mock({}, { data_source: 'pending_m4', ttl: 30 })
    renderPage()
    await waitFor(() => expect(screen.getByText(/risk telemetry producer/)).toBeInTheDocument())
  })
  it('real metrics → KPI tiles', async () => {
    mock({ portfolio_heat: 0.12, open_positions: 3 }, { data_source: 'timescaledb', ttl: 30 })
    renderPage()
    await waitFor(() => expect(screen.getByText('組合熱度')).toBeInTheDocument())
    expect(screen.getByText('持倉數')).toBeInTheDocument()
  })
})
