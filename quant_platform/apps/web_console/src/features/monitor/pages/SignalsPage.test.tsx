import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { SignalsPage } from './SignalsPage'

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
        <SignalsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

describe('SignalsPage', () => {
  it('telemetry → signal rows', async () => {
    mockByPath({
      '/monitor/signals': {
        data: [{ signal_time: '2023-01-03T00:00:00', strategy_id: 'inst_flow', stock_id: '2454', action: 'buy', priority: 2, submitted: true }],
        meta: { data_source: 'timescaledb' },
      },
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText('2454').length).toBeGreaterThan(0))
  })
  it('pending → PendingNote', async () => {
    mockByPath({}) // all pending (signals/fills + funnel/timeline)
    renderPage()
    await waitFor(() => expect(screen.getAllByText(/待紙上交易遙測/).length).toBeGreaterThan(0))
  })
})
