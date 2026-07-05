import { describe, expect, it } from 'vitest'
import {
  bandTone,
  cellSign,
  dsrToPercent,
  evalCriterion,
  fmtPct,
  heatAlphaPct,
  reconstructBusinessDays,
} from './reportViz'

describe('dsrToPercent', () => {
  it('maps the scale endpoints and mid to 0 / 100 / 50', () => {
    expect(dsrToPercent(0.85)).toBe(0)
    expect(dsrToPercent(1.0)).toBe(100)
    expect(dsrToPercent(0.925)).toBeCloseTo(50, 6)
  })
  it('places the two band boundaries at thirds', () => {
    expect(dsrToPercent(0.9)).toBeCloseTo(33.333, 2) // PAPER_WATCH lower
    expect(dsrToPercent(0.95)).toBeCloseTo(66.667, 2) // REAL lower
  })
  it('clamps out-of-domain values to the edges (never overflows the ruler)', () => {
    expect(dsrToPercent(0.5)).toBe(0)
    expect(dsrToPercent(1.4)).toBe(100)
  })
})

describe('bandTone', () => {
  it('maps the three bands to gain / warning / loss and unknown to muted', () => {
    expect(bandTone('REAL')).toBe('gain')
    expect(bandTone('PAPER_WATCH')).toBe('warning')
    expect(bandTone('REJECTED')).toBe('loss')
    expect(bandTone(null)).toBe('muted')
    expect(bandTone('???')).toBe('muted')
  })
})

describe('cellSign', () => {
  it('separates positive, negative, and no-tint (null / 0)', () => {
    expect(cellSign(0.03)).toBe('pos')
    expect(cellSign(-0.02)).toBe('neg')
    expect(cellSign(0)).toBe('none') // a real flat month is not tinted
    expect(cellSign(null)).toBe('none') // no-data month is not tinted
  })
})

describe('heatAlphaPct', () => {
  it('scales intensity with magnitude and caps, null → 0', () => {
    expect(heatAlphaPct(null)).toBe(0)
    expect(heatAlphaPct(0)).toBe(0)
    expect(heatAlphaPct(0.2, 0.1)).toBe(60) // above cap → max
    expect(heatAlphaPct(0.05, 0.1)).toBe(36) // half cap → mid
  })
})

describe('evalCriterion', () => {
  it('evaluates the gate ops honestly, missing metric → null (no light)', () => {
    expect(evalCriterion(1.2, '>=', 1.0)).toBe(true)
    expect(evalCriterion(0.8, '>=', 1.0)).toBe(false)
    expect(evalCriterion(-0.1, '<=', -0.2)).toBe(false)
    expect(evalCriterion(null, '>=', 1.0)).toBeNull()
    expect(evalCriterion(undefined, '>=', 1.0)).toBeNull()
    expect(evalCriterion(1.2, '~=', 1.0)).toBeNull() // unknown op
  })
})

describe('fmtPct', () => {
  it('formats a decimal ratio as % and null as a dash', () => {
    expect(fmtPct(0.1234)).toBe('12.34%')
    expect(fmtPct(-0.05)).toBe('-5.00%')
    expect(fmtPct(null)).toBe('—')
  })
})

describe('reconstructBusinessDays', () => {
  it('skips weekends from a Friday anchor (matches pandas freq="B")', () => {
    // 2020-01-03 is a Friday → next business days are Mon 06, Tue 07.
    expect(reconstructBusinessDays('2020-01-03', 3)).toEqual([
      '2020-01-03',
      '2020-01-06',
      '2020-01-07',
    ])
  })
  it('returns exactly n dates and an empty array for a bad anchor', () => {
    expect(reconstructBusinessDays('2020-01-01', 10)).toHaveLength(10)
    expect(reconstructBusinessDays('not-a-date', 5)).toEqual([])
  })
})
