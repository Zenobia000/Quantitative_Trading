/*
 * ReportViewerPage（Goal 5）—— fixture-mode 渲染測試。
 * 所有端點 stub 成 404 → getEvaluation fallback 到 bundled evaluation fixture（inst_flow deployment_strict）；
 * 驗五張 scorecard、not_available 態（Win Rate 整卡 + 各 not_available 指標）、fixture badge、decision bar。
 * ReportEquityChart 引 lightweight-charts（canvas）→ mock（同 RunReportPage.test 慣例）。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ReportViewerPage } from './ReportViewerPage'

vi.mock('../components/ReportEquityChart', () => ({
  ReportEquityChart: () => <div data-testid="equity-mock" />,
}))

// 所有端點 → 404（evaluation fallback fixture；run series 空 → 元件走已解釋空態）。
function notFound() {
  return { status: 404, json: async () => ({ detail: 'Not Found' }) }
}

function stubFixtureMode() {
  vi.stubGlobal('fetch', vi.fn(async () => notFound()) as unknown as typeof fetch)
}

// API 模式：/research/evaluations 回真 envelope（source=api → Live badge）。
function stubApiMode(evaluation: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = String(url)
      if (u.includes('/research/evaluations/')) {
        return { status: 200, json: async () => ({ success: true, data: evaluation, error: null, meta: {} }) }
      }
      return notFound()
    }) as unknown as typeof fetch,
  )
}

afterEach(() => vi.unstubAllGlobals())

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/research/reports/a1b9c3d4e5f6']}>
        <Routes>
          <Route path="/research/reports/:runId" element={<ReportViewerPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReportViewerPage · fixture mode', () => {
  it('falls back to the bundled fixture and shows the fixture data-source badge', async () => {
    stubFixtureMode()
    renderPage()
    await waitFor(() => expect(screen.getByText('Fixture 模式 · 尚未接後端')).toBeInTheDocument())
    // headline banner 三答：策略名（PageHeader subtitle + banner）+ verdict label + recommendation action
    expect(screen.getAllByText('inst_flow').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Weak')).toBeInTheDocument()
    expect(screen.getByText('eligible_for_live_oos')).toBeInTheDocument()
  })

  it('renders all five scorecards', async () => {
    stubFixtureMode()
    renderPage()
    await waitFor(() => expect(screen.getByTestId('scorecard-profitability')).toBeInTheDocument())
    for (const cat of ['profitability', 'risk', 'risk_adjusted', 'win_rate', 'liquidity']) {
      expect(screen.getByTestId(`scorecard-${cat}`)).toBeInTheDocument()
    }
    // 維度標籤（zh-TW；grid 卡 + tab 各一 → 至少一處）
    expect(screen.getAllByText('獲利能力').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('流動性').length).toBeGreaterThanOrEqual(1)
  })

  it('honestly renders the not_available Win Rate card with its reason', async () => {
    stubFixtureMode()
    renderPage()
    const card = await screen.findByTestId('scorecard-win_rate')
    // 整卡 not_available 狀態燈 + 契約原因文字（不留無說明佔位）
    expect(within(card).getByText('無法產出')).toBeInTheDocument()
    expect(within(card).getByText(/per-trade pnl/)).toBeInTheDocument()
  })

  it('renders the decision action bar with the fixture badge and marks optimistically', async () => {
    stubFixtureMode()
    renderPage()
    const keep = await screen.findByTestId('decision-keep')
    expect(screen.getByTestId('decision-archive')).toBeInTheDocument()
    expect(screen.getByTestId('decision-rerun')).toBeInTheDocument()
    expect(screen.getByTestId('decision-select_live_oos')).toBeInTheDocument()
    expect(screen.getByText('fixture 模式 —— 尚未接後端')).toBeInTheDocument()
    // 樂觀更新：點 Keep → 本地標記 badge
    fireEvent.click(keep)
    expect(screen.getByText(/已標記 保留/)).toBeInTheDocument()
  })

  it('switches sheet tab when a scorecard card is clicked', async () => {
    stubFixtureMode()
    renderPage()
    const riskCard = await screen.findByTestId('scorecard-risk')
    fireEvent.click(riskCard)
    // risk tab 明細表出現 risk 指標（Ulcer index 為 risk 卡獨有 label）
    await waitFor(() => expect(screen.getByText('Ulcer index')).toBeInTheDocument())
  })

  it('links the trade log to the run trade-review page with a partial caveat', async () => {
    stubFixtureMode()
    renderPage()
    await waitFor(() => expect(screen.getByText('開啟逐筆覆盤')).toBeInTheDocument())
    // Win Rate not_available → partial caveat note
    expect(screen.getByText(/僅再平衡列/)).toBeInTheDocument()
  })
})

describe('ReportViewerPage · api mode', () => {
  it('shows the Live API badge when the endpoint returns data', async () => {
    stubApiMode({
      schema_version: '1.0',
      evaluation_id: 'eval_x',
      run_id: 'run_x',
      strategy: 'demo_strat',
      profile: 'quick_triage',
      profile_version: '1.0',
      created_at: '2026-07-03T00:00:00+08:00',
      window: { is_start: '2015-01-01', is_end: '2024-12-31' },
      universe: { symbols_count: 100, bundle_ref: 'x', survivorship_clean: false },
      verdict: {
        label: 'Promising',
        truth_verdict: 'INCOMPLETE',
        recommendation: { action: 'keep_researching', confidence: 'low', reasons: ['triage only'] },
      },
      headline_metrics: { cagr: 0.2, sharpe: 1.3, max_drawdown: 0.15, dsr: null, oos_holdout_sharpe: null, trades: 30 },
      scorecards: [
        { category: 'profitability', status: 'pass', metrics: [] },
        { category: 'risk', status: 'pass', metrics: [] },
        { category: 'risk_adjusted', status: 'pass', metrics: [] },
        { category: 'win_rate', status: 'not_available', note: 'no per-trade pnl', metrics: [] },
        { category: 'liquidity', status: 'warn', metrics: [] },
      ],
      checks: [],
      sizing: { position_size: 0, reason: 'triage' },
      lineage: { config_hash: 'run_x', params: {}, engine: 'sim', bundle_ref: 'x', n_trials: 1, git_sha: null },
      report_pack_ref: 'x',
      data_gaps: [],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('即時 API')).toBeInTheDocument())
    expect(screen.getAllByText('demo_strat').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Promising')).toBeInTheDocument()
  })
})
