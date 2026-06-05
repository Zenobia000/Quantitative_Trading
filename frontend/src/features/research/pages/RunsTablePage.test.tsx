import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { RunsTablePage } from './RunsTablePage'

function mockRuns(rows: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      status: 200,
      json: async () => ({ success: true, data: rows, error: null, meta: { ttl: 300 } }),
    })) as unknown as typeof fetch,
  )
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/research/runs']}>
        <RunsTablePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('RunsTablePage', () => {
  it('populated → 顯示 run 列 + guardrail pending', async () => {
    mockRuns([{ run_id: 'run_abc', strategy_id: 's1', status: 'done', sharpe: 1.23 }])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_abc')).toBeInTheDocument())
    expect(screen.getByText('1.23')).toBeInTheDocument()
    // guardrail 端點未接線 → pending（不假造數字）
    expect(screen.getByText('待後端')).toBeInTheDocument()
  })

  it('zero run → FirstRunEmptyState', async () => {
    mockRuns([])
    renderPage()
    await waitFor(() => expect(screen.getByText('尚無策略，從第一次回測開始')).toBeInTheDocument())
  })
})
