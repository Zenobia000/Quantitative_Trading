/*
 * scorecardStatus 純函式：狀態→tone/符號、verdict/severity→tone、truth_verdict→band、值/門檻格式化。
 * 誠實未知（missing/not_applicable/not_available）一律中性、不亮警報。
 */
import { describe, expect, it } from 'vitest'
import {
  fmtMetricValue,
  fmtThreshold,
  isCardUnavailable,
  severityTone,
  statusMark,
  statusTone,
  truthVerdictToBand,
  verdictTone,
} from './scorecardStatus'

describe('statusTone / statusMark', () => {
  it('maps functional statuses to tones and keeps unknowns neutral', () => {
    expect(statusTone('pass')).toBe('gain')
    expect(statusTone('warn')).toBe('warning')
    expect(statusTone('fail')).toBe('error')
    expect(statusTone('not_available')).toBe('muted')
    expect(statusTone('not_applicable')).toBe('muted')
    expect(statusTone('missing')).toBe('muted')
  })

  it('pairs a text mark with each status (colour is never the only channel)', () => {
    expect(statusMark('pass')).toBe('✓')
    expect(statusMark('fail')).toBe('✗')
    expect(statusMark('warn')).toBe('△')
    expect(statusMark('not_available')).toBe('⊘')
  })
})

describe('verdictTone / severityTone / band', () => {
  it('maps verdict labels case-insensitively', () => {
    expect(verdictTone('Promising')).toBe('gain')
    expect(verdictTone('Weak')).toBe('warning')
    expect(verdictTone('Negative')).toBe('loss')
    expect(verdictTone('mystery')).toBe('muted')
    expect(verdictTone(null)).toBe('muted')
  })

  it('grades severity (block_deploy red, block_live_oos amber)', () => {
    expect(severityTone('block_deploy')).toBe('error')
    expect(severityTone('block_live_oos')).toBe('warning')
    expect(severityTone('info')).toBe('muted')
  })

  it('maps only real truth verdicts to a DSR band', () => {
    expect(truthVerdictToBand('PAPER_WATCH')).toBe('PAPER_WATCH')
    expect(truthVerdictToBand('REAL')).toBe('REAL')
    expect(truthVerdictToBand('INCOMPLETE')).toBeNull()
    expect(truthVerdictToBand(undefined)).toBeNull()
  })

  it('flags a not_available card', () => {
    expect(isCardUnavailable('not_available')).toBe(true)
    expect(isCardUnavailable('warn')).toBe(false)
  })
})

describe('fmtMetricValue / fmtThreshold', () => {
  it('formats fractions as percent and honest dashes for null', () => {
    expect(fmtMetricValue(0.162, 'fraction')).toBe('16.20%')
    expect(fmtMetricValue(1.025, 'ratio')).toBe('1.025')
    expect(fmtMetricValue(60, 'count')).toBe('60')
    expect(fmtMetricValue(null, 'fraction')).toBe('—')
    expect(fmtMetricValue(Number.NaN, 'ratio')).toBe('—')
  })

  it('builds an op+value threshold string, null when no threshold', () => {
    expect(fmtThreshold('>', 0.18, 'fraction')).toBe('> 18.0%')
    expect(fmtThreshold('>', 1.0, 'ratio')).toBe('> 1')
    expect(fmtThreshold(null, null, 'ratio')).toBeNull()
  })
})
