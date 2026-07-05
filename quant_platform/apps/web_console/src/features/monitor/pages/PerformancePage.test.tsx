import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { PerformancePage } from './PerformancePage'

function mockByPath(byPath: Record<string, { data: unknown; meta?: unknown }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const hit = Object.entries(byPath).find(([p]) => path.endsWith(p))?.[1]
      const body = hit ?? { data: [], meta: { data_source: 'pending' } }
      return { status: 200, json: async () => ({ success: true, data: body.data, error: null, meta: body.meta ?? { ttl: 60 } }) }
    }) as unknown as typeof fetch,
  )
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/monitor/performance']}>
        <PerformancePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('PerformancePage', () => {
  it('real telemetry → KPI tiles + equity rows', async () => {
    mockByPath({
      '/monitor/performance/kpi': { data: { current_equity: 10_200_000, total_return: 0.02, sharpe: 1.4 }, meta: { ttl: 300, data_source: 'timescaledb' } },
      '/monitor/performance/equity': { data: [{ t: '2023-01-03T00:00:00', equity: 10_200_000, drawdown: -0.01 }], meta: { ttl: 300, data_source: 'timescaledb' } },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Sharpe')).toBeInTheDocument())
    expect(screen.getByText('1.40')).toBeInTheDocument()
    expect(screen.getByText('↑ 2.00%')).toBeInTheDocument()
  })

  it('pending telemetry → PendingNote (no fabricated data)', async () => {
    mockByPath({}) // all pending
    renderPage()
    await waitFor(() => expect(screen.getAllByText(/待紙上交易遙測/).length).toBeGreaterThan(0))
  })
})
