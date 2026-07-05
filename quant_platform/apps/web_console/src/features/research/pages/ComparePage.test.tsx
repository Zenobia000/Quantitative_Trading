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
    // 真實 CompareReportData：回應為「物件」（非陣列），含 metric_keys + comparisons[]（doc 25 §6.1）
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        status: 200,
        json: async () => ({
          success: true,
          data: {
            baseline_id: 'run_a',
            metric_keys: ['sharpe'],
            sign_consistent: {},
            rankings: {},
            comparisons: [
              { run_id: 'run_a', is_baseline: true, metrics: { sharpe: 1.1 }, delta: {}, rank: {}, gate_status: 'PASS' },
              { run_id: 'run_b', is_baseline: false, metrics: { sharpe: 0.9 }, delta: { sharpe: -0.2 }, rank: {}, gate_status: 'FAIL' },
            ],
          },
          error: null,
          meta: {},
        }),
      })) as unknown as typeof fetch,
    )
    renderAt('/research/compare?run_ids=run_a,run_b')
    await waitFor(() => expect(screen.getByText('1.10')).toBeInTheDocument())
    // baseline 標記 ★ run_a 同時出現在 toolbar chip 與表格列（皆為 baseline 指示）
    expect(screen.getAllByText('★ run_a').length).toBeGreaterThan(0)
    expect(screen.getByText('0.90')).toBeInTheDocument() // run_b 的 sharpe
    expect(screen.getAllByText('待後端').length).toBeGreaterThan(1) // equity/parcoords/guardrail pending
  })
})
