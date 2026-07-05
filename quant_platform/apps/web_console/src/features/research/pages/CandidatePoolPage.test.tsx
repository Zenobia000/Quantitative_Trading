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

/**
 * api-mode flow mock: GET returns the *current* pool; POST decision / select-live-oos either
 * succeeds (server-folds the pool to `after`) or fails with a structured envelope error.
 * Records the last POST so tests can assert the request the UI made.
 */
interface PostRecord {
  url: string
  method: string
  body: unknown
}
function mockApiFlow(
  initial: Candidate[],
  opts: {
    after?: Candidate[]
    error?: { status: number; code: string; message: string; detail?: unknown }
  } = {},
): { posts: PostRecord[] } {
  const posts: PostRecord[] = []
  let current = initial
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
      const method = init?.method ?? 'GET'
      if (method === 'POST') {
        posts.push({ url: u, method, body: init?.body ? JSON.parse(String(init.body)) : undefined })
        if (opts.error) {
          return {
            status: opts.error.status,
            json: async () => ({
              success: false,
              data: null,
              error: { code: opts.error!.code, message: opts.error!.message, detail: opts.error!.detail },
              meta: {},
            }),
          }
        }
        if (opts.after) current = opts.after
        return { status: 201, json: async () => ({ success: true, data: { decision_id: 'd1' }, error: null, meta: {} }) }
      }
      return {
        status: 200,
        json: async () => ({
          success: true,
          data: current,
          error: null,
          meta: { total: current.length, page: 1, limit: 50, data_source: 'ledger' },
        }),
      }
    }) as unknown as typeof fetch,
  )
  return { posts }
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

describe('CandidatePoolPage — fixture optimistic overlay (no backend write)', () => {
  it('non-eligible Select Live OOS forces an override reason, then applies locally with a local badge', async () => {
    // fixture mode = 404 fallback; decisions stay local (never a POST).
    const spy = vi.fn(async (_url: string, _init?: RequestInit) => ({
      status: 404,
      json: async () => ({ success: false, data: null, error: 'x', meta: {} }),
    }))
    vi.stubGlobal('fetch', spy as unknown as typeof fetch)
    renderPage()
    // four_layer_resonance is the fixture's not_recommended candidate.
    await waitFor(() => expect(screen.getByText('four_layer_resonance')).toBeInTheDocument())

    const card = screen.getByText('four_layer_resonance').closest('section') as HTMLElement
    fireEvent.click(within(card).getByRole('button', { name: '選入 Live OOS' }))
    const dialog = screen.getByRole('dialog')
    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'worth a paper-replay look' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '送出' }))

    // local overlay: state → live_oos_selected + a "not synced" local badge; no POST issued.
    await waitFor(() => expect(screen.getAllByText('已選 Live OOS').length).toBeGreaterThan(0))
    expect(screen.getByText('本地未同步')).toBeInTheDocument()
    const posts = spy.mock.calls.filter((c) => (c[1] as RequestInit | undefined)?.method === 'POST')
    expect(posts.length).toBe(0)
  })
})

describe('CandidatePoolPage — api mode (real mutations)', () => {
  it('live envelope → no fixture badge, shows connected badge', async () => {
    mockCandidates({ data: [candidate()] })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())
    expect(screen.queryByText('fixture 模式 — 尚未接後端')).not.toBeInTheDocument()
    expect(screen.getByText('已接後端')).toBeInTheDocument()
  })

  it('Archive → reason dialog → POST /decision {action:archive,reason}; refetch folds to archived', async () => {
    const { posts } = mockApiFlow([candidate({ state: 'promising' })], {
      after: [candidate({ state: 'archived' })],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '封存' }))
    const dialog = screen.getByRole('dialog')
    const submit = within(dialog).getByRole('button', { name: '送出' })
    expect(submit).toBeDisabled()
    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'landscape PBO too high' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '送出' }))

    // archived + hidden by default → card leaves the default view (proves the server write took).
    await waitFor(() => expect(screen.queryByText('x_strategy')).not.toBeInTheDocument())
    const post = posts.find((p) => p.url.includes('/decision'))
    expect(post).toBeTruthy()
    expect(post!.url).toContain('/research/candidates/cand_x/decision')
    expect(post!.body).toEqual({ action: 'archive', reason: 'landscape PBO too high' })
  })

  it('eligible Select Live OOS → POST /select-live-oos {override:false} without a reason dialog', async () => {
    const { posts } = mockApiFlow([candidate({ state: 'promising', live_oos_recommendation: 'eligible' })], {
      after: [candidate({ state: 'live_oos_selected', live_oos_recommendation: 'eligible' })],
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '選入 Live OOS' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await waitFor(() => expect(screen.getAllByText('已選 Live OOS').length).toBeGreaterThan(0))
    // api mode never uses the local overlay → no "not synced" badge.
    expect(screen.queryByText('本地未同步')).not.toBeInTheDocument()
    const post = posts.find((p) => p.url.includes('/select-live-oos'))
    expect(post!.body).toEqual({ reason: undefined, override: false, observation_kind: 'paper_replay' })
  })

  it('non-eligible Select Live OOS → override reason → POST /select-live-oos {override:true,reason}', async () => {
    const { posts } = mockApiFlow(
      [candidate({ state: 'promising', live_oos_recommendation: 'not_recommended' })],
      { after: [candidate({ state: 'live_oos_selected', live_oos_recommendation: 'not_recommended' })] },
    )
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '選入 Live OOS' }))
    const dialog = screen.getByRole('dialog')
    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'paper-replay probe' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '送出' }))

    await waitFor(() => expect(screen.getAllByText('已選 Live OOS').length).toBeGreaterThan(0))
    const post = posts.find((p) => p.url.includes('/select-live-oos'))
    expect(post!.body).toEqual({ reason: 'paper-replay probe', override: true, observation_kind: 'paper_replay' })
  })

  it('blocked selection 409 → error surfaces inside the reason dialog (not silent)', async () => {
    mockApiFlow([candidate({ state: 'promising', live_oos_recommendation: 'blocked' })], {
      error: { status: 409, code: 'IS_GATE_NOT_PASSED', message: "candidate 'cand_x' recommendation is 'blocked'", detail: { state: 'promising' } },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '選入 Live OOS' }))
    const dialog = screen.getByRole('dialog')
    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'try anyway' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '送出' }))

    // dialog stays open, shows the backend message via an alert.
    await waitFor(() => expect(within(dialog).getByRole('alert')).toBeInTheDocument())
    expect(within(dialog).getByText(/blocked/)).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('illegal transition 400 on a no-reason action → page-level error banner (not silent)', async () => {
    // keep from a state the machine forbids → 400 with a hint; keep needs no reason dialog.
    mockApiFlow([candidate({ state: 'promising' })], {
      error: { status: 400, code: 'BAD_REQUEST', message: 'illegal transition', detail: { hint: "cannot 'keep' from state 'promising'" } },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('x_strategy')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '保留' }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByText(/illegal transition/)).toBeInTheDocument()
    expect(screen.getByText(/cannot 'keep' from state/)).toBeInTheDocument()
  })
})
