import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { WiredPage } from './WiredPage'

function renderWired(meta: Record<string, unknown>, data: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ status: 200, json: async () => ({ success: true, data, error: null, meta }) })) as unknown as typeof fetch,
  )
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <WiredPage title="績效總覽" route="/monitor/performance" spec="monitor_a_performance" endpoint="/monitor/performance/kpi" />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('WiredPage', () => {
  it('pending 端點 → pending note + section 結構', async () => {
    renderWired({ data_source: 'pending_m4', ttl: 300 }, {})
    await waitFor(() => expect(screen.getByText(/typed-empty/)).toBeInTheDocument())
    // design.pen section 結構（monitor_a 有 equity_curve 等）
    expect(screen.getByText('equity_curve')).toBeInTheDocument()
  })
})
