import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { HomePage } from './HomePage'

// 依 URL 精確路由 mock：research-status/recent 真資料；fleet/system-health 回
// typed-empty PENDING（對齊後端 home.py M4-deferred stub）。
function mockHome() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = String(url)
      let body: unknown
      if (u.includes('research-status')) {
        body = { success: true, data: { total_runs: 3, latest_gate_status: 'FAIL', is_gate_blocker: null, trials: null, dsr: null }, error: null, meta: { data_source: 'ledger' } }
      } else if (u.includes('recent')) {
        body = { success: true, data: [{ type: 'run', run_id: 'run_a', preset: 'v3', gate_status: 'FAIL' }], error: null, meta: { data_source: 'ledger' } }
      } else if (u.includes('system-health')) {
        body = { success: true, data: {}, error: null, meta: { data_source: 'pending' } }
      } else {
        body = { success: true, data: [], error: null, meta: { data_source: 'pending' } } // /home/fleet
      }
      return { status: 200, json: async () => body }
    }) as unknown as typeof fetch,
  )
}

afterEach(() => vi.unstubAllGlobals())

function renderHome() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('HomePage', () => {
  it('research-status + recent 真接；fleet pending 誠實佔位', async () => {
    mockHome()
    renderHome()
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument()) // total_runs
    expect(screen.getByText('run_a')).toBeInTheDocument()
    // fleet endpoint pending → PendingNote（待後端）出現
    await waitFor(() => expect(screen.getAllByText('待後端').length).toBeGreaterThan(0))
  })

  it('system-health pending 時狀態帶不假造 CLEAR/PAPER/OFFLINE', async () => {
    mockHome()
    renderHome()
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument())
    // 舊版硬編碼的假狀態值不得再出現
    expect(screen.queryByText('CLEAR')).not.toBeInTheDocument()
    expect(screen.queryByText('PAPER')).not.toBeInTheDocument()
    expect(screen.queryByText('OFFLINE')).not.toBeInTheDocument()
  })
})
