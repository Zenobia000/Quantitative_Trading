import { describe, expect, it } from 'vitest'
import { toCandlestickData, toSeriesMarkers } from './candleTransform'
import type { RunCandle, RunMarker } from '../api/candles'

const COLORS = { gain: '#22c55e', loss: '#f87171' }

describe('toCandlestickData', () => {
  it('maps OHLC preserving time string, dropping volume', () => {
    const candles: RunCandle[] = [
      { time: '2020-01-01', open: 10, high: 12, low: 9, close: 11, volume: 100 },
    ]
    expect(toCandlestickData(candles)).toEqual([
      { time: '2020-01-01', open: 10, high: 12, low: 9, close: 11 },
    ])
  })

  it('returns empty array for empty input', () => {
    expect(toCandlestickData([])).toEqual([])
  })
})

describe('toSeriesMarkers', () => {
  it('entry → belowBar arrowUp, gain color, price label', () => {
    const markers: RunMarker[] = [{ time: '2020-01-01', kind: 'entry', price: 100 }]
    const [m] = toSeriesMarkers(markers, COLORS)
    expect(m).toMatchObject({
      time: '2020-01-01',
      position: 'belowBar',
      shape: 'arrowUp',
      color: COLORS.gain,
    })
    expect(m.text).toContain('進')
    expect(m.text).toContain('100.00')
  })

  it('winning exit → aboveBar arrowDown, gain color, +ret label', () => {
    const markers: RunMarker[] = [{ time: '2020-01-03', kind: 'exit', price: 110, ret: 0.1 }]
    const [m] = toSeriesMarkers(markers, COLORS)
    expect(m).toMatchObject({ position: 'aboveBar', shape: 'arrowDown', color: COLORS.gain })
    expect(m.text).toContain('10.0%')
  })

  it('losing exit → loss color', () => {
    const markers: RunMarker[] = [{ time: '2020-01-03', kind: 'exit', price: 90, ret: -0.1 }]
    const [m] = toSeriesMarkers(markers, COLORS)
    expect(m.color).toBe(COLORS.loss)
    expect(m.text).toContain('-10.0%')
  })

  it('exit without ret → neutral loss-safe label (>=0 treated as gain)', () => {
    const markers: RunMarker[] = [{ time: '2020-01-03', kind: 'exit', price: 90 }]
    const [m] = toSeriesMarkers(markers, COLORS)
    expect(m.color).toBe(COLORS.gain) // undefined ret ⇒ 0 ⇒ up
    expect(m.text).toBe('出')
  })

  it('preserves round-trip order (entry before exit)', () => {
    const markers: RunMarker[] = [
      { time: '2020-01-01', kind: 'entry', price: 100 },
      { time: '2020-01-03', kind: 'exit', price: 110, ret: 0.1 },
    ]
    const out = toSeriesMarkers(markers, COLORS)
    expect(out.map((m) => m.shape)).toEqual(['arrowUp', 'arrowDown'])
  })
})
