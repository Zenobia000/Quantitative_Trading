import { describe, expect, it } from 'vitest'
import {
  actionEnabled,
  applyDecision,
  candidateStateTone,
  reasonRequired,
  recommendationTone,
  runIdFromReportRef,
  scorecardGlyph,
  scorecardTone,
  truthVerdictTone,
} from './candidateDisplay'
import type { Candidate, CandidateState, LiveOosRecommendation } from '../../api/candidates'

function candidate(over: Partial<Candidate> = {}): Candidate {
  return {
    candidate_id: 'cand_x',
    strategy: 'x',
    hypothesis: 'h',
    created_at: '2026-07-01T00:00:00+08:00',
    state: 'triaged',
    latest_evaluation_id: 'eval_x',
    latest_profile: 'quick_triage',
    latest_label: 'Promising',
    latest_truth_verdict: null,
    live_oos_recommendation: 'eligible',
    scorecard_summary: {
      profitability: 'pass',
      risk: 'pass',
      risk_adjusted: 'pass',
      win_rate: 'not_available',
      liquidity: 'warn',
    },
    headline: {
      sharpe: 1.2,
      oos_holdout_sharpe: null,
      cagr: 0.2,
      max_drawdown: 0.18,
      dsr: 0.9,
      trades: 80,
      avg_turnover: null,
      survivorship_clean: true,
    },
    report_pack_ref: 'reports/research_runs/deadbeef01/manifest.json',
    next_action: 'na',
    decisions: [],
    ...over,
  }
}

describe('candidateStateTone', () => {
  it('maps primary states to distinct semantic tones', () => {
    expect(candidateStateTone('promising')).toBe('gain')
    expect(candidateStateTone('weak')).toBe('warning')
    expect(candidateStateTone('negative')).toBe('loss')
    expect(candidateStateTone('data_issue')).toBe('error')
    expect(candidateStateTone('live_oos_selected')).toBe('gain')
    expect(candidateStateTone('archived')).toBe('muted')
  })
  it('unknown state → muted', () => {
    expect(candidateStateTone('nonsense')).toBe('muted')
  })
})

describe('scorecard tone + glyph (dual-encoding)', () => {
  it('status → tone', () => {
    expect(scorecardTone('pass')).toBe('gain')
    expect(scorecardTone('warn')).toBe('warning')
    expect(scorecardTone('fail')).toBe('loss')
    expect(scorecardTone('not_available')).toBe('muted')
  })
  it('status → distinct shape glyph (not colour-only)', () => {
    expect(scorecardGlyph('pass')).toBe('●')
    expect(scorecardGlyph('warn')).toBe('◐')
    expect(scorecardGlyph('fail')).toBe('✕')
    expect(scorecardGlyph('not_available')).toBe('–')
  })
})

describe('recommendation + truth verdict tone (info only)', () => {
  it('recommendation', () => {
    expect(recommendationTone('eligible')).toBe('gain')
    expect(recommendationTone('not_recommended')).toBe('warning')
    expect(recommendationTone('blocked')).toBe('error')
  })
  it('truth verdict', () => {
    expect(truthVerdictTone('REAL')).toBe('gain')
    expect(truthVerdictTone('PAPER_WATCH')).toBe('warning')
    expect(truthVerdictTone('REJECTED')).toBe('error')
    expect(truthVerdictTone(null)).toBe('muted')
  })
})

describe('runIdFromReportRef', () => {
  it('parses the run hash from a report_pack_ref', () => {
    expect(runIdFromReportRef('reports/research_runs/a1b9c3d4e5f6/manifest.json')).toBe('a1b9c3d4e5f6')
  })
  it('null / malformed → null', () => {
    expect(runIdFromReportRef(null)).toBeNull()
    expect(runIdFromReportRef(undefined)).toBeNull()
    expect(runIdFromReportRef('nope')).toBeNull()
  })
})

describe('actionEnabled', () => {
  it('select Live OOS disabled for terminal/queued/data_issue states', () => {
    for (const s of ['archived', 'live_oos_selected', 'live_oos_running', 'live_oos_done', 'data_issue'] as CandidateState[]) {
      expect(actionEnabled(candidate({ state: s }), 'select_live_oos')).toBe(false)
    }
    expect(actionEnabled(candidate({ state: 'promising' }), 'select_live_oos')).toBe(true)
  })
  it('keep / archive disabled once archived; rerun always enabled', () => {
    const arch = candidate({ state: 'archived' })
    expect(actionEnabled(arch, 'keep')).toBe(false)
    expect(actionEnabled(arch, 'archive')).toBe(false)
    expect(actionEnabled(arch, 'rerun')).toBe(true)
  })
})

describe('reasonRequired (contract §6.3 override rule)', () => {
  it('archive always requires a reason', () => {
    expect(reasonRequired(candidate(), 'archive')).toBe(true)
  })
  it('select Live OOS requires reason iff recommendation is not eligible', () => {
    const reco = (r: LiveOosRecommendation) => candidate({ live_oos_recommendation: r })
    expect(reasonRequired(reco('eligible'), 'select_live_oos')).toBe(false)
    expect(reasonRequired(reco('not_recommended'), 'select_live_oos')).toBe(true)
    expect(reasonRequired(reco('blocked'), 'select_live_oos')).toBe(true)
  })
  it('keep / rerun never require a reason', () => {
    expect(reasonRequired(candidate(), 'keep')).toBe(false)
    expect(reasonRequired(candidate(), 'rerun')).toBe(false)
  })
})

describe('applyDecision (immutable optimistic update)', () => {
  it('archive → new object, state archived, appended decision carries reason', () => {
    const c = candidate({ state: 'weak' })
    const next = applyDecision(c, 'archive', '  landscape PBO too high  ', '2026-07-03T00:00:00Z')
    expect(next).not.toBe(c)
    expect(c.state).toBe('weak') // original untouched
    expect(next.state).toBe('archived')
    expect(next.decisions).toHaveLength(1)
    expect(next.decisions[0]).toMatchObject({
      action: 'archive',
      from_state: 'weak',
      to_state: 'archived',
      reason: 'landscape PBO too high',
      evaluation_ref: 'eval_x',
    })
  })
  it('non-eligible select is recorded as override_select', () => {
    const c = candidate({ state: 'promising', live_oos_recommendation: 'not_recommended' })
    const next = applyDecision(c, 'select_live_oos', 'worth a paper-replay look')
    expect(next.state).toBe('live_oos_selected')
    expect(next.decisions[0].action).toBe('override_select')
  })
  it('eligible select is recorded as select_live_oos', () => {
    const c = candidate({ state: 'promising', live_oos_recommendation: 'eligible' })
    const next = applyDecision(c, 'select_live_oos', undefined)
    expect(next.decisions[0].action).toBe('select_live_oos')
    expect(next.decisions[0].reason).toBeNull()
  })
})
