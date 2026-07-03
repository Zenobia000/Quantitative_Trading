import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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
    // n_configs / est_minutes are now interpolated into one localized estimate string
    await waitFor(() => expect(screen.getByText(/6 組參數/)).toBeInTheDocument())
    expect(screen.getByText(/約 3 分鐘/)).toBeInTheDocument()
    expect(screen.getAllByText('待後端').length).toBeGreaterThan(0) // heatmap/job pending
  })
})
