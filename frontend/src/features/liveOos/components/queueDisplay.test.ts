import { describe, it, expect } from 'vitest'
import {
  isBerthKind,
  kindTone,
  observationPct,
  queueStateTone,
  runIdFromReportRef,
} from './queueDisplay'

describe('queueStateTone', () => {
  it('running is gain, paused/expired warn, terminal/queued muted', () => {
    expect(queueStateTone('running')).toBe('gain')
    expect(queueStateTone('paused')).toBe('warning')
    expect(queueStateTone('expired')).toBe('warning')
    expect(queueStateTone('completed')).toBe('muted')
    expect(queueStateTone('queued')).toBe('muted')
    expect(queueStateTone('cancelled')).toBe('muted')
  })
  it('unknown state falls back to muted', () => {
    expect(queueStateTone('teleported')).toBe('muted')
  })
})

describe('kindTone / isBerthKind', () => {
  it('berth kinds are gain-toned and berth-shaped', () => {
    expect(kindTone('paper_watch_berth')).toBe('gain')
    expect(isBerthKind('paper_watch_berth')).toBe(true)
    expect(isBerthKind('after_close')).toBe(true)
  })
  it('paper_replay is muted and not berth-shaped (a one-shot batch, no window)', () => {
    expect(kindTone('paper_replay')).toBe('muted')
    expect(isBerthKind('paper_replay')).toBe(false)
  })
})

describe('runIdFromReportRef', () => {
  it('extracts the run_id from a report pack manifest path', () => {
    expect(runIdFromReportRef('reports/research_runs/a1b9c3d4e5f6/manifest.json')).toBe('a1b9c3d4e5f6')
  })
  it('returns null for a null / non-matching ref', () => {
    expect(runIdFromReportRef(null)).toBeNull()
    expect(runIdFromReportRef('reports/other/x.json')).toBeNull()
  })
})

describe('observationPct', () => {
  it('clamps 0..100 and rounds', () => {
    expect(observationPct(12, 90)).toBe(13)
    expect(observationPct(90, 90)).toBe(100)
    expect(observationPct(100, 90)).toBe(100) // clamp
  })
  it('returns 0 when data is missing', () => {
    expect(observationPct(null, 90)).toBe(0)
    expect(observationPct(5, null)).toBe(0)
    expect(observationPct(5, 0)).toBe(0)
  })
})
