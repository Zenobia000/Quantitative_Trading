/*
 * Smoke test：jsdom 無 canvas，故 mock 'lightweight-charts'，只驗元件正確調用
 * createChart / addSeries（權益線 + 回撤面積）/ setData，並在 oos_start 有值時
 * 疊「sealed」marker、卸載時 remove。真圖渲染留給 Playwright e2e。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactElement } from 'react'
import { cleanup, render } from '@testing-library/react'

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
  LineSeries: { type: 'Line' },
  AreaSeries: { type: 'Area' },
  ColorType: { Solid: 'solid' },
}))

const { setData, addSeries, remove, createChart, createSeriesMarkers } = h

import { ReportEquityChart } from './ReportEquityChart'
import { ThemeProvider } from '@/app/theme'

function renderChart(el: ReactElement) {
  return render(<ThemeProvider>{el}</ThemeProvider>)
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

const EQUITY = [1.0, 1.02, 1.01, 1.03]
const DRAWDOWN = [0, 0, -0.01, 0]

describe('ReportEquityChart', () => {
  it('creates a chart with an equity line + a drawdown area and sets both', () => {
    renderChart(
      <ReportEquityChart equity={EQUITY} drawdown={DRAWDOWN} isStart="2020-01-01" oosStart={null} />,
    )
    expect(createChart).toHaveBeenCalledOnce()
    expect(addSeries).toHaveBeenCalledTimes(2) // equity line + drawdown area
    expect(setData).toHaveBeenCalledTimes(2)
    // equity series data is date-indexed {time, value}
    const eqData = setData.mock.calls[0][0]
    expect(eqData[0]).toMatchObject({ value: 1.0 })
    expect(typeof eqData[0].time).toBe('string')
  })

  it('overlays a sealed marker at oos_start when the truth-gate window is present', () => {
    renderChart(
      <ReportEquityChart
        equity={EQUITY}
        drawdown={DRAWDOWN}
        isStart="2020-01-01"
        oosStart="2020-01-03"
      />,
    )
    expect(createSeriesMarkers).toHaveBeenCalledOnce()
    const markers = createSeriesMarkers.mock.calls[0][1]
    expect(markers[0]).toMatchObject({ time: '2020-01-03', text: '封存' })
  })

  it('draws no sealed marker when oos_start is null (no fabricated boundary)', () => {
    renderChart(
      <ReportEquityChart equity={EQUITY} drawdown={DRAWDOWN} isStart="2020-01-01" oosStart={null} />,
    )
    expect(createSeriesMarkers).not.toHaveBeenCalled()
  })

  it('removes the chart on unmount', () => {
    const { unmount } = renderChart(
      <ReportEquityChart equity={EQUITY} drawdown={DRAWDOWN} isStart="2020-01-01" oosStart={null} />,
    )
    unmount()
    expect(remove).toHaveBeenCalledOnce()
  })
})
