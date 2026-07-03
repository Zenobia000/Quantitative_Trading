/*
 * RunReportPage v1：三源（GET /runs/{id} · /report · /equity）→ 判決卡 + KPI + 分段 equity
 * + 月報酬熱圖 + 回撤事件 + 成本敏感 + Open-in-notebook。report 形狀對齊
 * backtest_platform/api/routers/runs_report.py 的 assembly（api.gen.ts RunReportData）。
 * ReportEquityChart 引 lightweight-charts（canvas）→ mock 掉（圖表另有 smoke test）。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RunReportPage } from './RunReportPage'

vi.mock('../components/ReportEquityChart', () => ({
  ReportEquityChart: ({ equity, oosStart }: { equity: unknown[]; oosStart: string | null }) => (
    <div data-testid="equity-mock">{`equity:${equity.length} oos:${oosStart ?? 'none'}`}</div>
  ),
}))

const RUN = {
  run_id: 'run_x',
  strategy: 's1',
  gate_status: 'PASS',
  engine: 'sim',
  window: ['2020-01-01', '2024-12-31'],
  metrics: { sharpe: 1.5, cagr: 0.32, maxdd: -0.18, win: 0.55, trades: 42, slippage_sharpe: 1.2 },
}

// Assembly 形狀（每欄可 null）：verdict + segments + monthly + dd + cost。
const REPORT = {
  run_id: 'run_x',
  verdict: {
    gate_status: 'PASS',
    gate_summary: null,
    criteria: [{ key: 'sharpe', op: '>=', threshold: 1.0, kind: 'edge', label: 'Sharpe 門檻' }],
    validation: null,
    truth_gate: { verdict_dsr: 0.97, band: 'REAL', state: 'active', source: 'watch_registry' },
  },
  segments: {
    run_window: { is_start: '2020-01-01', is_end: '2024-12-31' },
    truth_gate_window: { is_start: '2020-01-01', oos_start: '2023-01-02', is_end: '2024-12-31' },
  },
  monthly_returns: {
    years: [2020],
    matrix: [[0.03, -0.01, null, null, null, null, null, null, null, null, null, null]],
    annual: [0.05],
    basis: 'reconstructed_business_days_from_is_start',
  },
  monthly_returns_note: null,
  drawdown_events: [
    {
      peak_idx: 1,
      trough_idx: 3,
      recovery_idx: 5,
      peak_date: '2020-01-06',
      trough_date: '2020-01-08',
      recovery_date: '2020-01-10',
      depth: 0.12,
      duration_bars: 4,
      recovered: true,
    },
  ],
  cost_sensitivity: { sharpe: 1.5, slippage_sharpe: 1.2 },
}

const EQUITY = { run_id: 'run_x', equity: [1.0, 1.02, 1.01, 1.03], drawdown: [0, 0, -0.01, 0] }

function envelope(data: unknown) {
  return { status: 200, json: async () => ({ success: true, data, error: null, meta: {} }) }
}

function stubFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = String(url)
      if (u.endsWith('/report')) return envelope(REPORT)
      if (u.endsWith('/equity')) return envelope(EQUITY)
      return envelope(RUN) // GET /runs/{id}
    }) as unknown as typeof fetch,
  )
}

afterEach(() => vi.unstubAllGlobals())

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/research/runs/run_x']}>
        <Routes>
          <Route path="/research/runs/:id" element={<RunReportPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RunReportPage v1', () => {
  it('renders the verdict card (gate badge + DSR band) and KPIs', async () => {
    stubFetch()
    renderPage()
    await waitFor(() => expect(screen.getByText('通過')).toBeInTheDocument()) // gate PASS big badge
    expect(screen.getByText('42')).toBeInTheDocument() // trades KPI (unique)
    expect(screen.getByText(/REAL/)).toBeInTheDocument() // DSR band
    expect(screen.getByText('Sharpe 門檻')).toBeInTheDocument() // criteria light
  })

  it('renders the segmented equity chart wired with the sealed oos_start', async () => {
    stubFetch()
    renderPage()
    await waitFor(() =>
      expect(screen.getByTestId('equity-mock')).toHaveTextContent('equity:4 oos:2023-01-02'),
    )
  })

  it('renders the monthly heatmap, drawdown events, and cost sensitivity', async () => {
    stubFetch()
    renderPage()
    await waitFor(() => expect(screen.getByText('回撤事件（前 5 深）')).toBeInTheDocument())
    expect(screen.getByText('-12.00%')).toBeInTheDocument() // dd depth
    expect(screen.getByText('月報酬熱圖')).toBeInTheDocument()
    expect(screen.getByText('成本敏感度')).toBeInTheDocument()
  })

  it('exposes an Open-in-notebook link pointing at /runs/{id}/notebook', async () => {
    stubFetch()
    renderPage()
    await waitFor(() => expect(screen.getByRole('link')).toBeInTheDocument())
    expect(screen.getByRole('link')).toHaveAttribute('href', '/runs/run_x/notebook')
  })
})
