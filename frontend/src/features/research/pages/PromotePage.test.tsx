import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { PromotePage } from './PromotePage'

afterEach(() => vi.unstubAllGlobals())

function stubFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const isAudit = String(url).endsWith('/audit')
      return {
        status: 200,
        json: async () => ({
          success: true,
          data: isAudit
            ? [{ strategy_id: 's1', stage: 'paper', note: 'looks good', actor: 'zeno', at: '2026-06-07T10:00:00' }]
            : {
                strategy_id: 's1',
                stage: 'paper',
                gates: [
                  { stage: 'draft', reached: true },
                  { stage: 'paper', reached: true },
                  { stage: 'live', reached: false },
                ],
                history: [],
              },
          error: null,
          meta: {},
        }),
      }
    }) as unknown as typeof fetch,
  )
}

function renderAt(path = '/research/promote/s1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/research/promote/:strategyId" element={<PromotePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PromotePage', () => {
  it('renders current stage + stepper gates + next-stage advance control', async () => {
    stubFetch()
    renderAt()
    // current stage badge + the "advance to live" affordance (paper → live)
    await waitFor(() => expect(screen.getByText(/晉升至 live/)).toBeInTheDocument())
    expect(screen.getAllByText('paper').length).toBeGreaterThan(0)
  })

  it('shows the immutable audit trail', async () => {
    stubFetch()
    renderAt()
    await waitFor(() => expect(screen.getByText('looks good')).toBeInTheDocument())
  })
})
