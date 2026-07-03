import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { LiveOosQueuePage } from './LiveOosQueuePage'
import type { LiveOosQueueItem } from '../api/queue'

function item(over: Partial<LiveOosQueueItem> = {}): LiveOosQueueItem {
  return {
    queue_id: 'loq_x_1',
    candidate_id: 'cand_x',
    strategy: 'x_strategy',
    evaluation_id: 'eval_x',
    selected_at: '2026-07-02T19:10:00+08:00',
    selected_by: 'operator',
    selection_reason: 'PAPER_WATCH band; collect 3-month live OOS.',
    recommendation_at_selection: 'eligible',
    override: false,
    state: 'running',
    observation: {
      kind: 'paper_watch_berth',
      watch_registry_ref: 'x_strategy',
      dsr_band: 'watch',
      verdict_dsr: 0.908,
      enrolled_on: '2026-07-02',
      expiry_date: '2026-09-30',
      observation_days: 90,
      observed_trading_days: 12,
      days_remaining: 78,
      position_size: 0.0,
    },
    report_pack_ref: 'reports/research_runs/deadbeef01/manifest.json',
    links: {
      report: 'GET /research/evaluations/eval_x/report',
      candidate: 'GET /research/candidates/cand_x',
      strategy_asset: 'GET /research/strategies/x_strategy',
    },
    ...over,
  }
}

function mockQueue(mode: { fail?: boolean; data?: LiveOosQueueItem[] }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      if (mode.fail) {
        return { status: 404, json: async () => ({ success: false, data: null, error: 'not found', meta: {} }) }
      }
      return {
        status: 200,
        json: async () => ({
          success: true,
          data: mode.data ?? [],
          error: null,
          meta: { total: (mode.data ?? []).length, page: 1, limit: 50, data_source: 'watch_registry' },
        }),
      }
    }) as unknown as typeof fetch,
  )
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/live-oos/queue']}>
        <LiveOosQueuePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('LiveOosQueuePage — fixture fallback', () => {
  it('404 → falls back to the bundled fixture with a fixture-mode badge', async () => {
    mockQueue({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('fixture 模式 — 契約範例示範')).toBeInTheDocument())
    // fixture spans 5 items; inst_flow appears twice (running + expired berth)
    expect(screen.getAllByText('inst_flow').length).toBe(2)
    expect(screen.getByText('four_layer_resonance')).toBeInTheDocument()
    expect(screen.getByText('momentum')).toBeInTheDocument()
    expect(screen.getByText('reversal')).toBeInTheDocument()
  })

  it('surfaces every state badge (running/queued/paused/completed/expired visible)', async () => {
    mockQueue({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('four_layer_resonance')).toBeInTheDocument())
    expect(screen.getAllByText('進行中').length).toBeGreaterThan(0) // running
    expect(screen.getAllByText('待跑').length).toBeGreaterThan(0) // queued
    expect(screen.getAllByText('已暫停').length).toBeGreaterThan(0) // paused
    expect(screen.getAllByText('已完成').length).toBeGreaterThan(0) // completed
    expect(screen.getAllByText('觀察期滿').length).toBeGreaterThan(0) // expired
  })

  it('state filter narrows to a single state', async () => {
    mockQueue({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('momentum')).toBeInTheDocument())
    // click the "paused" chip → only momentum's paused berth remains
    fireEvent.click(screen.getByRole('button', { name: /已暫停/ }))
    expect(screen.getByText('momentum')).toBeInTheDocument()
    expect(screen.queryByText('four_layer_resonance')).not.toBeInTheDocument()
  })
})

describe('LiveOosQueuePage — audit + links + kinds', () => {
  it('shows the selection audit (who + reason) and the override marker', async () => {
    mockQueue({
      data: [
        item({
          strategy: 'ov_strategy',
          override: true,
          override_reason: 'worth a paper-replay look',
          selection_reason: 'promising triage',
        }),
      ],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('ov_strategy')).toBeInTheDocument())
    expect(screen.getByText(/由 operator 於 2026-07-02 勾選/)).toBeInTheDocument()
    expect(screen.getByText('promising triage')).toBeInTheDocument()
    expect(screen.getByText('override 勾選')).toBeInTheDocument()
    expect(screen.getByText(/worth a paper-replay look/)).toBeInTheDocument()
  })

  it('links each item back to report / candidate / strategy asset', async () => {
    mockQueue({ data: [item()] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())
    expect(screen.getByRole('link', { name: '研究報表' })).toHaveAttribute('href', '/research/reports/deadbeef01')
    expect(screen.getByRole('link', { name: '候選池' })).toHaveAttribute('href', '/research/candidates')
    expect(screen.getByRole('link', { name: '策略資產' })).toHaveAttribute('href', '/research/strategies/x_strategy')
  })

  it('renders a berth observation progress bar for a berth kind', async () => {
    mockQueue({ data: [item()] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '13') // 12/90 → 13%
    expect(screen.getByText('12/90')).toBeInTheDocument()
  })

  it('shows the replay verdict for a completed paper_replay (no progress bar)', async () => {
    mockQueue({
      data: [
        item({
          strategy: 'replay_strategy',
          state: 'completed',
          observation: { ...item().observation, kind: 'paper_replay', watch_registry_ref: null, verdict_dsr: null },
          run: { run_id: 'paper_replay_replay_strategy_20260703', gate_status: 'REJECTED' },
        }),
      ],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('replay_strategy')).toBeInTheDocument())
    expect(screen.getByText('REJECTED')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })
})

describe('LiveOosQueuePage — states', () => {
  it('empty queue → onboarding empty state pointing at the Candidate Pool', async () => {
    mockQueue({ data: [] })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText('尚無勾選進 Live OOS 的策略')).toBeInTheDocument(),
    )
    expect(screen.getByRole('button', { name: '前往候選池勾選' })).toBeInTheDocument()
  })

  it('live envelope → connected badge, no fixture banner', async () => {
    mockQueue({ data: [item()] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())
    expect(screen.queryByText('fixture 模式 — 契約範例示範')).not.toBeInTheDocument()
    expect(screen.getByText('已接後端')).toBeInTheDocument()
  })
})
