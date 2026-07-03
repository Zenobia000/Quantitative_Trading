import { describe, expect, it } from 'vitest'
import { isPartial, isPending } from './domain'

// A1: isPending is now an EXACT match on the DataSource.PENDING token — the old
// startsWith('pending') mis-classified 'partial' and the retired 'pending_m4'.
describe('isPending / isPartial (doc 25 §5.4 DataSource vocabulary)', () => {
  it('isPending is true only for the exact "pending" token', () => {
    expect(isPending({ data_source: 'pending' })).toBe(true)
  })

  it('isPending is false for live tokens and for partial', () => {
    for (const src of ['timescaledb', 'watch_registry', 'parquet_scan', 'ledger', 'catalog', 'partial']) {
      expect(isPending({ data_source: src })).toBe(false)
    }
  })

  it('isPending is false for the retired pending_m4 token (backend unified → "pending")', () => {
    expect(isPending({ data_source: 'pending_m4' })).toBe(false)
  })

  it('isPending is false when meta / data_source is absent', () => {
    expect(isPending(undefined)).toBe(false)
    expect(isPending({})).toBe(false)
  })

  it('isPartial is true only for the exact "partial" token', () => {
    expect(isPartial({ data_source: 'partial' })).toBe(true)
    expect(isPartial({ data_source: 'pending' })).toBe(false)
    expect(isPartial(undefined)).toBe(false)
  })
})
