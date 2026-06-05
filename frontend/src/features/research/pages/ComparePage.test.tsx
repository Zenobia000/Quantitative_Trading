import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ComparePage } from './ComparePage'

function renderAt(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <ComparePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('ComparePage', () => {
  it('<2 run → 提示請選 ≥2', () => {
    renderAt('/research/compare?run_ids=run_a')
    expect(screen.getByText(/請至少選 2 個 run/)).toBeInTheDocument()
  })

  it('≥2 run → 顯示 chips + metric 表 + 多個 pending', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        status: 200,
        json: async () => ({
          success: true,
          data: [{ run_id: 'run_a', sharpe: 1.1 }, { run_id: 'run_b', sharpe: 0.9 }],
          error: null,
          meta: {},
        }),
      })) as unknown as typeof fetch,
    )
    renderAt('/research/compare?run_ids=run_a,run_b')
    await waitFor(() => expect(screen.getByText('1.10')).toBeInTheDocument())
    expect(screen.getByText('★ run_a')).toBeInTheDocument()
    expect(screen.getAllByText('待後端').length).toBeGreaterThan(1) // equity/parcoords/guardrail pending
  })
})
