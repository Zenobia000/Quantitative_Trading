/*
 * BranchExperimentsSection（Goal 9）—— 分支實驗 section 單測。
 * 驗：列分支（delta chips + status/origin）、evaluate 只在 draft+applies_to_rerun 出現、
 * overlay-only 誠實「不可評測」、compare 展開後端 delta 表、建分支需 parent、手動 fork POST。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { BranchExperimentsSection } from './BranchExperimentsSection'
import { coerceValue } from './BranchCreateDialog'
import type { BranchExperiment } from '../../api/branches'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function branch(over: Partial<BranchExperiment> = {}): BranchExperiment {
  return {
    branch_id: 'branch_momentum_aaa111',
    parent_evaluation_id: 'eval_momentum_x',
    parent_run_id: 'run_parent',
    strategy: 'momentum',
    profile: 'quick_triage',
    origin: 'manual',
    note: 'longer window',
    config_delta: [{ key: 'lookback_days', from: 60, to: 90 }],
    branch_config: { lookback_days: 90 },
    applies_to_rerun: true,
    created_at: '2026-07-03T09:00:00+08:00',
    evaluation_id: null,
    status: 'draft',
    ...over,
  }
}

const COMPARE = {
  branch_id: 'branch_momentum_aaa111',
  strategy: 'momentum',
  parent_evaluation_id: 'eval_momentum_x',
  parent_run_id: 'run_parent',
  branch_evaluation_id: 'eval_momentum_b',
  branch_run_id: 'run_branch',
  config_delta: [{ key: 'lookback_days', from: 60, to: 90 }],
  branch_evaluated: true,
  metrics: [
    { metric: 'sharpe', lower_is_better: false, parent: 1.0, branch: 1.4, delta: 0.4, change: 'improved' },
    { metric: 'max_drawdown', lower_is_better: true, parent: 0.3, branch: 0.25, delta: -0.05, change: 'improved' },
  ],
  decision: { verdict: 'branch_better', parent_label: 'Weak', branch_label: 'Promising', reasons: [] },
}

function stub(branches: BranchExperiment[], extra?: Record<string, unknown>) {
  const box = { evals: 0, creates: 0 }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
      const method = init?.method ?? 'GET'
      const path = new URL(u, 'http://x').pathname
      const ok = (data: unknown, status = 200) => ({ status, json: async () => ({ success: true, data, error: null, meta: { ttl: 300 } }) })
      if (path === '/research/branches' && method === 'GET') return ok(branches)
      if (path === '/research/branches' && method === 'POST') {
        box.creates += 1
        return ok(branch({ branch_id: 'branch_momentum_new', origin: 'manual' }), 201)
      }
      if (path.endsWith('/evaluate') && method === 'POST') {
        box.evals += 1
        return ok(branch({ status: 'evaluated', evaluation_id: 'eval_b' }), 201)
      }
      if (path.endsWith('/compare')) return ok(extra?.compare ?? COMPARE)
      return { status: 404, json: async () => ({ success: false, data: null, error: { code: 'NOT_FOUND', message: 'nf' }, meta: {} }) }
    }) as unknown as typeof fetch,
  )
  return box
}

function renderSection(props: Parameters<typeof BranchExperimentsSection>[0]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <BranchExperimentsSection {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('coerceValue', () => {
  it('parses numbers, booleans, and falls back to string', () => {
    expect(coerceValue('90')).toBe(90)
    expect(coerceValue('0.25')).toBe(0.25)
    expect(coerceValue('true')).toBe(true)
    expect(coerceValue('false')).toBe(false)
    expect(coerceValue('monthly')).toBe('monthly')
  })
})

describe('BranchExperimentsSection', () => {
  it('lists a draft config-key branch with delta chips + an evaluate button', async () => {
    stub([branch()])
    renderSection({ strategy: 'momentum', parentEvaluationId: 'eval_momentum_x', configFields: ['lookback_days'] })
    await waitFor(() => expect(screen.getByTestId('branch-row')).toBeInTheDocument())
    expect(screen.getByText(/lookback_days: 60 → 90/)).toBeInTheDocument()
    expect(screen.getByTestId('branch-evaluate')).toBeInTheDocument()
  })

  it('overlay-only draft branch honestly shows "not evaluable" (no evaluate button)', async () => {
    stub([branch({ applies_to_rerun: false, origin: 'simulation', config_delta: [{ key: 'slippage_bps', from: 0, to: 10 }] })])
    renderSection({ strategy: 'momentum', parentEvaluationId: 'eval_momentum_x', configFields: ['lookback_days'] })
    await waitFor(() => expect(screen.getByTestId('branch-not-evaluable')).toBeInTheDocument())
    expect(screen.queryByTestId('branch-evaluate')).not.toBeInTheDocument()
  })

  it('evaluate button posts to the evaluate endpoint', async () => {
    const box = stub([branch()])
    renderSection({ strategy: 'momentum', parentEvaluationId: 'eval_momentum_x', configFields: ['lookback_days'] })
    await waitFor(() => expect(screen.getByTestId('branch-evaluate')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('branch-evaluate'))
    await waitFor(() => expect(box.evals).toBe(1))
  })

  it('compare toggle on an evaluated branch renders the backend delta table', async () => {
    stub([branch({ status: 'evaluated', evaluation_id: 'eval_b' })])
    renderSection({ strategy: 'momentum', parentEvaluationId: 'eval_momentum_x', configFields: ['lookback_days'] })
    await waitFor(() => expect(screen.getByTestId('branch-compare-toggle')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('branch-compare-toggle'))
    await waitFor(() => expect(screen.getByTestId('branch-compare-table')).toBeInTheDocument())
    expect(screen.getByTestId('branch-delta-sharpe').textContent).toContain('+')
  })

  it('create button is disabled without a parent evaluation (nothing to fork from)', async () => {
    stub([])
    renderSection({ strategy: 'momentum', parentEvaluationId: null, configFields: ['lookback_days'] })
    await waitFor(() => expect(screen.getByTestId('branch-create-open')).toBeDisabled())
  })

  it('manual create dialog forks a branch (POST /research/branches)', async () => {
    const box = stub([])
    renderSection({ strategy: 'momentum', parentEvaluationId: 'eval_momentum_x', configFields: ['lookback_days', 'top_fraction'] })
    await waitFor(() => expect(screen.getByTestId('branch-create-open')).not.toBeDisabled())
    fireEvent.click(screen.getByTestId('branch-create-open'))
    fireEvent.change(screen.getByTestId('branch-create-value'), { target: { value: '90' } })
    fireEvent.click(screen.getByTestId('branch-create-submit'))
    await waitFor(() => expect(box.creates).toBe(1))
  })
})
