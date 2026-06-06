import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { StrategyLibraryPage } from './StrategyLibraryPage'

function mockStrategies(rows: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      status: 200,
      json: async () => ({ success: true, data: rows, error: null, meta: { total: rows.length } }),
    })) as unknown as typeof fetch,
  )
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <StrategyLibraryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('StrategyLibraryPage', () => {
  it('roster → 顯示策略卡 + 狀態雙編碼', async () => {
    mockStrategies([
      { strategy_id: 'v3', version: 'v3', best_kpi: { sharpe: 0.9 }, validation_status: 'is_fail', stage: 'draft', runs_count: 2 },
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('is_fail')).toBeInTheDocument())
    expect(screen.getAllByText('v3').length).toBeGreaterThan(0)
    expect(screen.getByText('2 runs')).toBeInTheDocument()
  })

  it('零策略 → FirstRunEmptyState', async () => {
    mockStrategies([])
    renderPage()
    await waitFor(() => expect(screen.getByText('尚無策略，從第一次回測開始')).toBeInTheDocument())
  })
})
