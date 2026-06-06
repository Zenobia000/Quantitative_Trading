import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { HomePage } from './HomePage'

function mockHome() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const body =
        String(url).includes('research-status')
          ? { success: true, data: { total_runs: 3, latest_gate_status: 'FAIL', is_gate_blocker: null, trials: null, dsr: null }, error: null, meta: {} }
          : { success: true, data: [{ type: 'run', run_id: 'run_a', preset: 'v3', gate_status: 'FAIL' }], error: null, meta: {} }
      return { status: 200, json: async () => body }
    }) as unknown as typeof fetch,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('HomePage', () => {
  it('research-status + recent 真接；fleet/system-health pending', async () => {
    mockHome()
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument()) // total_runs
    expect(screen.getByText('run_a')).toBeInTheDocument()
    expect(screen.getAllByText('待後端').length).toBeGreaterThan(1) // fleet + system-health pending
  })
})
