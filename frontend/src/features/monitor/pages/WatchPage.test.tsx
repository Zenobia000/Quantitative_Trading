import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { WatchPage } from './WatchPage'
import type { WatchRow } from '../hooks/useWatch'

// A realistic overview row — mirrors the backend `_status_dict` + timer-health
// enrichment exactly (mock-shape drift would otherwise mask a real contract drift).
function row(over: Partial<WatchRow> = {}): WatchRow {
  return {
    strategy: 'inst_flow',
    status: 'active',
    enrolled_on: '2026-06-01',
    verdict_dsr: 0.908,
    observed_trading_days: 22,
    nominal_trading_days: 60,
    expiry_date: '2026-08-30',
    days_remaining: 59,
    timer_health: 'ok',
    last_session_date: '2026-07-03',
    last_session_at: '2026-07-03T14:32:05+08:00',
    last_trading_day: '2026-07-03',
    sessions: [{ date: '2026-07-03', status: 'OK' }],
    ...over,
  }
}

/** Stateful fetch mock: GET reflects the latest pause/resume POST. */
function mockWatch(initial: WatchRow[]) {
  let rows = initial
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = new URL(url, 'http://x').pathname
      const method = init?.method ?? 'GET'
      const envelope = (data: unknown, meta: unknown = { data_source: 'watch_registry', ttl: 60 }) => ({
        status: 200,
        json: async () => ({ success: true, data, error: null, meta }),
      })
      if (method === 'POST') {
        const m = path.match(/\/monitor\/watch\/([^/]+)\/(pause|resume)/)
        const strategy = decodeURIComponent(m![1])
        const nextStatus = m![2] === 'pause' ? 'paused' : 'active'
        rows = rows.map((r) => (r.strategy === strategy ? { ...r, status: nextStatus as WatchRow['status'] } : r))
        const updated = rows.find((r) => r.strategy === strategy)!
        return envelope(updated, { data_source: 'watch_registry' })
      }
      return envelope(rows)
    }) as unknown as typeof fetch,
  )
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <WatchPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('WatchPage', () => {
  it('active berth → status badge, observation progress, ok timer, session timeline', async () => {
    mockWatch([row()])
    renderPage()
    await waitFor(() => expect(screen.getByText('inst_flow')).toBeInTheDocument())
    expect(screen.getByText('觀察中')).toBeInTheDocument()
    expect(screen.getByText('22/~60')).toBeInTheDocument()
    expect(screen.getByText('排程正常')).toBeInTheDocument()
    expect(screen.getByText(/最後成功 session 2026-07-03/)).toBeInTheDocument()
    expect(screen.getByText('OK')).toBeInTheDocument()
  })

  it('stale timer → warning + copyable systemd command', async () => {
    mockWatch([row({ timer_health: 'stale', last_session_date: '2026-07-02', last_trading_day: '2026-07-03' })])
    renderPage()
    await waitFor(() => expect(screen.getByText('排程可能未在跑')).toBeInTheDocument())
    expect(screen.getByText('systemctl --user enable --now after-close.timer')).toBeInTheDocument()
    expect(screen.getByText(/上一交易日 2026-07-03/)).toBeInTheDocument()
  })

  it('never_ran timer → install guidance (warning, no last session)', async () => {
    mockWatch([row({ timer_health: 'never_ran', last_session_date: null, sessions: [] })])
    renderPage()
    await waitFor(() => expect(screen.getByText('尚未執行')).toBeInTheDocument())
    expect(screen.getByText('systemctl --user enable --now after-close.timer')).toBeInTheDocument()
    expect(screen.getByText('尚無 session 紀錄')).toBeInTheDocument()
  })

  it('pause button → POSTs pause and re-renders as paused', async () => {
    mockWatch([row()])
    renderPage()
    await waitFor(() => expect(screen.getByText('暫停觀察 ⏸')).toBeInTheDocument())
    fireEvent.click(screen.getByText('暫停觀察 ⏸'))
    await waitFor(() => expect(screen.getByText('已暫停')).toBeInTheDocument())
    // now shows the resume affordance
    expect(screen.getByText('恢復觀察 ▶')).toBeInTheDocument()
  })

  it('empty overview → honest empty state, no fabricated berth', async () => {
    mockWatch([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/目前無觀察艙艙位/)).toBeInTheDocument())
  })
})
