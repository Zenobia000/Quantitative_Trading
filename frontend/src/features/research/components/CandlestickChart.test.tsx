/*
 * Smoke test：jsdom 無 canvas，故 mock 'lightweight-charts'，只驗元件正確調用
 * createChart / addSeries / setData / createSeriesMarkers 並在卸載時 remove。
 * 真圖渲染留給 Playwright e2e（不在此假造 canvas）。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render } from '@testing-library/react'

// vi.mock is hoisted above imports, so the fakes must be created via vi.hoisted
// (also hoisted) to be referencable both inside the factory and in the tests.
const h = vi.hoisted(() => {
  const setData = vi.fn()
  const addSeries = vi.fn(() => ({ setData }))
  const fitContent = vi.fn()
  const applyOptions = vi.fn()
  const remove = vi.fn()
  const createChart = vi.fn(() => ({
    addSeries,
    timeScale: () => ({ fitContent }),
    applyOptions,
    remove,
  }))
  const createSeriesMarkers = vi.fn()
  return { setData, addSeries, fitContent, applyOptions, remove, createChart, createSeriesMarkers }
})

vi.mock('lightweight-charts', () => ({
  createChart: h.createChart,
  createSeriesMarkers: h.createSeriesMarkers,
  CandlestickSeries: { type: 'Candlestick' },
  ColorType: { Solid: 'solid' },
}))

const { setData, addSeries, remove, createChart, createSeriesMarkers } = h

import { CandlestickChart } from './CandlestickChart'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

const CANDLES = [{ time: '2020-01-01', open: 10, high: 12, low: 9, close: 11, volume: 100 }]
const MARKERS = [{ time: '2020-01-01', kind: 'entry' as const, price: 10 }]

describe('CandlestickChart', () => {
  it('creates a chart, sets candle data, and overlays markers', () => {
    render(<CandlestickChart candles={CANDLES} markers={MARKERS} />)
    expect(createChart).toHaveBeenCalledOnce()
    expect(addSeries).toHaveBeenCalledOnce()
    expect(setData).toHaveBeenCalledWith([
      { time: '2020-01-01', open: 10, high: 12, low: 9, close: 11 },
    ])
    expect(createSeriesMarkers).toHaveBeenCalledOnce()
    const passedMarkers = createSeriesMarkers.mock.calls[0][1]
    expect(passedMarkers[0]).toMatchObject({ shape: 'arrowUp', position: 'belowBar' })
  })

  it('removes the chart on unmount', () => {
    const { unmount } = render(<CandlestickChart candles={CANDLES} markers={MARKERS} />)
    unmount()
    expect(remove).toHaveBeenCalledOnce()
  })
})
