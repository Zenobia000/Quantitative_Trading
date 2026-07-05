import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { PromotePage } from './PromotePage'

afterEach(() => vi.unstubAllGlobals())

/**
 * 依 pathname 路由三個真實端點的形狀：
 * - GET /research/promote/s1          → PromotionStateData {strategy_id, stage, gates[], history[]}
 * - GET /research/promote/s1/audit    → PromotionEvent[] {strategy_id, stage, note, actor, at}
 * - GET /research/strategies          → StrategyRow[]（gate 前置證據：validation_status）
 */
function stubFetch(validationStatus = 'is_pass') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(String(url), 'http://x').pathname
      let data: unknown
      if (path.endsWith('/research/strategies')) {
        data = [{ strategy_id: 's1', version: 's1', best_kpi: {}, validation_status: validationStatus, stage: 'draft', runs_count: 3 }]
      } else if (path.endsWith('/audit')) {
        data = [{ strategy_id: 's1', stage: 'paper', note: 'looks good', actor: 'zeno', at: '2026-06-07T10:00:00' }]
      } else {
        data = {
          strategy_id: 's1',
          stage: 'paper',
          gates: [
            { stage: 'draft', reached: true },
            { stage: 'paper', reached: true },
            { stage: 'live', reached: false },
          ],
          history: [],
        }
      }
      return { status: 200, json: async () => ({ success: true, data, error: null, meta: {} }) }
    }) as unknown as typeof fetch,
  )
}

function renderAt(path = '/deploy/promote/s1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/deploy/promote/:strategyId" element={<PromotePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PromotePage', () => {
  it('renders current stage + stepper gates + next-stage advance control', async () => {
    stubFetch('is_pass')
    renderAt()
    // current stage badge + the "advance to live" affordance (paper → live)
    // stage enums are now localized (paper → '紙上交易', live → '實盤')
    await waitFor(() => expect(screen.getByText(/晉升至 實盤/)).toBeInTheDocument())
    expect(screen.getAllByText('紙上交易').length).toBeGreaterThan(0)
  })

  it('shows the immutable audit trail', async () => {
    stubFetch('is_pass')
    renderAt()
    await waitFor(() => expect(screen.getByText('looks good')).toBeInTheDocument())
  })

  it('gate PASS 證據存在 → advance 鈕可用', async () => {
    stubFetch('is_pass')
    renderAt()
    await waitFor(() => expect(screen.getByText(/晉升至 實盤/)).toBeInTheDocument())
    expect(screen.getByText(/晉升至 實盤/).closest('button')).not.toBeDisabled()
  })

  it('無 gate PASS 證據 → advance 鈕 disabled + 說明文字（前端防線）', async () => {
    stubFetch('is_fail')
    renderAt()
    await waitFor(() => expect(screen.getByText(/晉升至 實盤/)).toBeInTheDocument())
    expect(screen.getByText(/晉升至 實盤/).closest('button')).toBeDisabled()
    expect(screen.getByText(/尚無 IS gate PASS/)).toBeInTheDocument()
  })
})
