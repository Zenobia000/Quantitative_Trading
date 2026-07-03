import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { SweepPage } from './SweepPage'

afterEach(() => vi.unstubAllGlobals())

describe('SweepPage', () => {
  it('estimate 接真實 /runs/estimate → 顯示 N configs / est min', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        status: 200,
        json: async () => ({ success: true, data: { n_configs: 6, est_minutes: 3.0, axes: {} }, error: null, meta: {} }),
      })) as unknown as typeof fetch,
    )
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <SweepPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByText('6')).toBeInTheDocument())
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getAllByText('待後端').length).toBeGreaterThan(0) // heatmap/job pending
  })

  it('A4: an expired/unknown sweep job (404 poll) shows an error, not infinite queued', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        const u = String(url)
        if (u.includes('/runs/estimate')) {
          return {
            status: 200,
            json: async () => ({ success: true, data: { n_configs: 6, est_minutes: 3.0, axes: {} }, error: null, meta: {} }),
          }
        }
        if (u.includes('/research/sweep') && init?.method === 'POST') {
          return {
            status: 202,
            json: async () => ({ success: true, data: { job_id: 'j1', status: 'queued' }, error: null, meta: {} }),
          }
        }
        // GET /research/sweep/j1/status → 404 (unknown/expired job, doc 25 §5.2)
        return {
          status: 404,
          json: async () => ({
            success: false,
            data: null,
            error: { code: 'NOT_FOUND', message: 'not found', detail: { resource: 'job', id: 'j1' } },
            meta: null,
          }),
        }
      }) as unknown as typeof fetch,
    )
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <SweepPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByText('提交掃描')).toBeInTheDocument())
    fireEvent.click(screen.getByText('提交掃描'))
    await waitFor(() => expect(screen.getByText(/任務狀態查詢失敗/)).toBeInTheDocument())
    expect(screen.queryByText('queued')).not.toBeInTheDocument() // not stuck pending
  })
})
