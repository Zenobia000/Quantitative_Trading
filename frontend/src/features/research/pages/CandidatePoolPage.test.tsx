import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { CandidatePoolPage } from './CandidatePoolPage'
import type { Candidate } from '../api/candidates'

/** Full contract-shaped candidate factory for api-mode tests. */
function candidate(over: Partial<Candidate> = {}): Candidate {
  return {
    candidate_id: 'cand_x',
    strategy: 'x_strategy',
    hypothesis: 'a testable hypothesis',
    created_at: '2026-07-01T00:00:00+08:00',
    state: 'promising',
    latest_evaluation_id: 'eval_x',
    latest_profile: 'quick_triage',
    latest_label: 'Promising',
    latest_truth_verdict: null,
    live_oos_recommendation: 'eligible',
    scorecard_summary: {
      profitability: 'pass',
      risk: 'pass',
      risk_adjusted: 'pass',
      win_rate: 'pass',
      liquidity: 'warn',
    },
    headline: {
      sharpe: 1.31,
      oos_holdout_sharpe: null,
      cagr: 0.22,
      max_drawdown: 0.188,
      dsr: 0.9,
      trades: 84,
      avg_turnover: null,
      survivorship_clean: true,
    },
    report_pack_ref: 'reports/research_runs/deadbeef01/manifest.json',
    next_action: 'run fixed_hypothesis_oos next',
    decisions: [],
    ...over,
  }
}

/** Mock fetch for GET /research/candidates: either a live envelope or a 404 (→ fixture fallback). */
function mockCandidates(mode: { fail?: boolean; data?: Candidate[] }) {
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
          meta: { total: (mode.data ?? []).length, page: 1, limit: 50, data_source: 'ledger' },
        }),
      }
    }) as unknown as typeof fetch,
  )
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/research/candidates']}>
        <CandidatePoolPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('CandidatePoolPage — fixture fallback', () => {
  it('404 → falls back to bundled fixture, shows fixture-mode badge', async () => {
    mockCandidates({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('fixture 模式 — 尚未接後端')).toBeInTheDocument())
    // 5 fixture candidates span every state; the 4 non-archived render, archived hidden by default.
    expect(screen.getByText('inst_flow')).toBeInTheDocument()
    expect(screen.getByText('momentum')).toBeInTheDocument()
    expect(screen.getByText('four_layer_resonance')).toBeInTheDocument()
    expect(screen.getByText('reversal')).toBeInTheDocument()
    expect(screen.queryByText('long_short')).not.toBeInTheDocument()
  })

  it('archived toggle reveals the archived candidate (bad/archived stays discoverable)', async () => {
    mockCandidates({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('inst_flow')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('checkbox'))
    expect(screen.getByText('long_short')).toBeInTheDocument()
  })

  it('state chip filters to a single state', async () => {
    mockCandidates({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('momentum')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /負向/ }))
    expect(screen.getByText('momentum')).toBeInTheDocument()
    expect(screen.queryByText('inst_flow')).not.toBeInTheDocument()
  })

  it('text search filters by strategy name', async () => {
    mockCandidates({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('inst_flow')).toBeInTheDocument())
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'momentum' } })
    await waitFor(() => expect(screen.queryByText('inst_flow')).not.toBeInTheDocument())
    expect(screen.getByText('momentum')).toBeInTheDocument()
  })

  it('renders the five-scorecard mini lights with accessible names', async () => {
    mockCandidates({ fail: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('inst_flow')).toBeInTheDocument())
    // inst_flow: profitability=warn, risk=pass → accessible names encode status textually (not colour-only).
    expect(screen.getAllByLabelText('風險: 通過').length).toBeGreaterThan(0)
  })
})

describe('CandidatePoolPage — api mode', () => {
  it('live envelope → no fixture badge, shows connected badge', async () => {
    mockCandidates({ data: [candidate()] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())
    expect(screen.queryByText('fixture 模式 — 尚未接後端')).not.toBeInTheDocument()
    expect(screen.getByText('已接後端')).toBeInTheDocument()
  })
})

describe('CandidatePoolPage — reason enforcement', () => {
  it('Archive opens the reason dialog; submit blocked until a reason is typed', async () => {
    mockCandidates({ data: [candidate({ state: 'promising' })] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '封存' }))
    const dialog = screen.getByRole('dialog')
    const submit = within(dialog).getByRole('button', { name: '送出' })
    expect(submit).toBeDisabled()

    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'landscape PBO too high' } })
    expect(submit).toBeEnabled()
    fireEvent.click(submit)

    // archived + hidden by default → card leaves the default view (proves the decision applied).
    await waitFor(() => expect(screen.queryByText('x_strategy')).not.toBeInTheDocument())
  })

  it('non-eligible Select Live OOS forces an override reason, then applies locally', async () => {
    mockCandidates({ data: [candidate({ state: 'promising', live_oos_recommendation: 'not_recommended' })] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '選入 Live OOS' }))
    const dialog = screen.getByRole('dialog')
    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'worth a paper-replay look' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '送出' }))

    // state → live_oos_selected surfaces on both the card badge and the derived chip.
    await waitFor(() => expect(screen.getAllByText('已選 Live OOS').length).toBeGreaterThan(0))
    expect(screen.getByText('本地未同步')).toBeInTheDocument()
  })

  it('eligible Select Live OOS applies directly with no reason dialog', async () => {
    mockCandidates({ data: [candidate({ state: 'promising', live_oos_recommendation: 'eligible' })] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '選入 Live OOS' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByText('已選 Live OOS').length).toBeGreaterThan(0))
    expect(screen.getByText('本地未同步')).toBeInTheDocument()
  })
})
