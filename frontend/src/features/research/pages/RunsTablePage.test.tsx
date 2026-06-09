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

  it('append-only ledger 重複 run_id → 表格去重為一 run 一列（F5）', async () => {
    // ledger may append the same run_id multiple times (DOE re-run) → dedupe by run_id
    mockRuns([
      { run_id: 'dup_run', strategy_id: 's1', status: 'done', sharpe: 1.1 },
      { run_id: 'dup_run', strategy_id: 's1', status: 'done', sharpe: 1.1 },
      { run_id: 'dup_run', strategy_id: 's1', status: 'done', sharpe: 1.1 },
      { run_id: 'uniq_run', strategy_id: 's2', status: 'done', sharpe: 0.9 },
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('dup_run')).toBeInTheDocument())
    // one checkbox per unique run → 2, not 4 (no duplicate React keys)
    expect(screen.getAllByRole('checkbox')).toHaveLength(2)
    expect(screen.getByText('顯示 2 筆')).toBeInTheDocument()
  })
})
