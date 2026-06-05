import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RunReportPage } from './RunReportPage'

function mockRun(run: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      status: 200,
      json: async () => ({ success: true, data: run, error: null, meta: {} }),
    })) as unknown as typeof fetch,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('RunReportPage', () => {
  it('顯示 KPI + reproduce + tear_sheet pending', async () => {
    mockRun({ run_id: 'run_x', strategy_id: 's1', status: 'done', sharpe: 1.5, total_return: 0.32 })
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/research/runs/run_x']}>
          <Routes>
            <Route path="/research/runs/:id" element={<RunReportPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByText('1.50')).toBeInTheDocument())
    expect(screen.getAllByText(/run_x/).length).toBeGreaterThan(0)
    expect(screen.getByText('待後端')).toBeInTheDocument() // tear_sheet pending
  })
})
