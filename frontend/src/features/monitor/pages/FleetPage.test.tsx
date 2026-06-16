import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { FleetPage } from './FleetPage'

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
        <FleetPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

describe('FleetPage', () => {
  it('pending → PendingNote (fleet awaits multi-strategy run)', async () => {
    mock([], { data_source: 'pending_m4' })
    renderPage()
    await waitFor(() => expect(screen.getByText(/待多策略實跑/)).toBeInTheDocument())
  })
  it('real fleet → strategy rows', async () => {
    mock([{ strategy_id: 'inst_flow', status: 'paper', weight: 0.25, sharpe: 1.5, equity: 10_000_000 }], { data_source: 'timescaledb' })
    renderPage()
    await waitFor(() => expect(screen.getByText('inst_flow')).toBeInTheDocument())
  })
})
