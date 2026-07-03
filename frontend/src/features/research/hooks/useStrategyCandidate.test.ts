import { describe, expect, it } from 'vitest'
import { candidatesByStrategy } from './useStrategyCandidate'
import type { Candidate } from '../api/candidates'

/** Minimal Candidate for pure-selector tests (only fields the selector touches matter). */
function cand(strategy: string, candidate_id: string, over: Partial<Candidate> = {}): Candidate {
  return {
    candidate_id,
    strategy,
    hypothesis: `${strategy} hypothesis`,
    created_at: '2026-06-14T10:00:00+08:00',
    state: 'triaged',
    latest_evaluation_id: `eval_${candidate_id}`,
    latest_profile: 'quick_triage',
    latest_label: 'Triaged',
    latest_truth_verdict: null,
    live_oos_recommendation: 'eligible',
    scorecard_summary: {
      profitability: 'pass',
      risk: 'pass',
      risk_adjusted: 'pass',
      win_rate: 'pass',
      liquidity: 'pass',
    },
    headline: {
      sharpe: 1,
      oos_holdout_sharpe: 1,
      cagr: 0.1,
      max_drawdown: 0.1,
      trades: 10,
      avg_turnover: 0.5,
      survivorship_clean: true,
    },
    report_pack_ref: `reports/research_runs/${candidate_id}/manifest.json`,
    next_action: 'next',
    decisions: [],
    ...over,
  }
}

describe('candidatesByStrategy', () => {
  it('undefined / empty list → empty map (honest no-op)', () => {
    expect(candidatesByStrategy(undefined).size).toBe(0)
    expect(candidatesByStrategy([]).size).toBe(0)
  })

  it('maps each strategy to its candidate', () => {
    const map = candidatesByStrategy([cand('four_layer', 'c1'), cand('inst_flow', 'c2')])
    expect(map.get('four_layer')?.candidate_id).toBe('c1')
    expect(map.get('inst_flow')?.candidate_id).toBe('c2')
    expect(map.get('unknown')).toBeUndefined()
  })

  it('newest-created-first pool → first (newest) candidate wins per strategy', () => {
    // API returns newest-created first, so the earlier array entry is the newest.
    const map = candidatesByStrategy([
      cand('four_layer', 'newest'),
      cand('four_layer', 'older'),
    ])
    expect(map.size).toBe(1)
    expect(map.get('four_layer')?.candidate_id).toBe('newest')
  })
})
