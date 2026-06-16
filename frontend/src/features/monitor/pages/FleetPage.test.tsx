import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { FleetPage } from './FleetPage'

function mockByPath(byPath: Record<string, { data: unknown; meta?: unknown }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const hit = Object.entries(byPath).find(([p]) => path.endsWith(p))?.[1]
      const body = hit ?? { data: [], meta: { data_source: 'pending_m4' } }
      return { status: 200, json: async () => ({ success: true, data: body.data, error: null, meta: body.meta ?? { ttl: 60 } }) }
    }) as unknown as typeof fetch,
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
  it('telemetry → portfolio summary + fleet rows', async () => {
    mockByPath({
      '/monitor/portfolio-summary': { data: { n_strategies: 2, total_equity: 19_930_000, total_open_positions: 5 }, meta: { data_source: 'timescaledb' } },
      '/monitor/fleet': {
        data: [{ strategy_id: 'inst_flow', equity: 10_130_000, cash: 8_600_000, open_positions: 3, portfolio_heat: 0.12, last_update: '2023-10-02T00:00:00' }],
        meta: { data_source: 'timescaledb' },
      },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('inst_flow')).toBeInTheDocument())
    expect(screen.getByText('在跑策略')).toBeInTheDocument()
  })

  it('pending → PendingNote (fleet awaits telemetry)', async () => {
    mockByPath({}) // all pending
    renderPage()
    await waitFor(() => expect(screen.getByText(/待多策略實跑/)).toBeInTheDocument())
  })
})
