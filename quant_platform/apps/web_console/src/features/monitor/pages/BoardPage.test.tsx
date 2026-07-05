import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { BoardPage } from './BoardPage'

function mock(data: unknown, meta: unknown = { ttl: 5, data_source: 'timescaledb' }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ status: 200, json: async () => ({ success: true, data, error: null, meta }) })) as unknown as typeof fetch,
  )
}
function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <BoardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

const doneRow = {
  run_id: 'a1b2c3d4e5f6', strategy: 'inst_flow', engine: 'sim',
  stocks: ['2330', '2317'], is_start: '2026-01-05', is_end: '2026-04-10',
  status: 'done', gate_status: 'PASS', gate_summary: 'IS gate: 4/4',
  metrics: { sharpe: 1.234 }, created_at: '2026-07-02T12:00:00+00:00',
}
const runningRow = {
  run_id: 'ffffffffffff', strategy: 'inst_flow', engine: 'sim',
  stocks: ['2454'], is_start: '2026-01-05', is_end: '2026-04-10',
  status: 'running', gate_status: null, gate_summary: null,
  metrics: null, created_at: '2026-07-02T12:01:00+00:00',
}

describe('BoardPage', () => {
  it('runs 表 → 看板列 + 判決 + sharpe', async () => {
    mock([doneRow, runningRow])
    renderPage()
    await waitFor(() => expect(screen.getByText('a1b2c3d4e5f6')).toBeInTheDocument())
    // gate/status 經 EnumBadge 本地化：PASS→通過、running→執行中
    expect(screen.getByText('通過')).toBeInTheDocument()
    expect(screen.getByText('1.234')).toBeInTheDocument()
    expect(screen.getByText('2330, 2317')).toBeInTheDocument()
    // in-flight run：verdict/metrics null → —（不捏造）
    expect(screen.getByText('執行中')).toBeInTheDocument()
  })
  it('pending → PendingNote', async () => {
    mock([], { data_source: 'pending' })
    renderPage()
    await waitFor(() => expect(screen.getByText(/待 TimescaleDB runs 表/)).toBeInTheDocument())
  })
})
