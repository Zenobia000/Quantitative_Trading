import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { RiskPage } from './RiskPage'

// byPath mock：每個端點回自己的 data/meta；未列出者預設 typed-empty pending。
function mockByPath(byPath: Record<string, { data: unknown; meta?: unknown }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const hit = Object.entries(byPath).find(([p]) => path.endsWith(p))?.[1]
      const body = hit ?? { data: [], meta: { data_source: 'pending' } }
      return { status: 200, json: async () => ({ success: true, data: body.data, error: null, meta: body.meta ?? { ttl: 30 } }) }
    }) as unknown as typeof fetch,
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
    mockByPath({}) // metrics + mdd-trend + events all pending
    renderPage()
    await waitFor(() => expect(screen.getByText(/risk telemetry producer/)).toBeInTheDocument())
  })
  it('real metrics → KPI tiles', async () => {
    mockByPath({
      '/monitor/risk/metrics': { data: { portfolio_heat: 0.12, open_positions: 3 }, meta: { data_source: 'timescaledb', ttl: 30 } },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('組合熱度')).toBeInTheDocument())
    expect(screen.getByText('持倉數')).toBeInTheDocument()
  })
})
