/*
 * 個股 K 線圖（TradingView lightweight-charts v5，ADR-034）。
 * 疊 entry ▲ / exit ▼ marker；漲跌沿用 gain/loss 語義（設計 spec §candlestick_chart 例外）。
 * 純轉換在 lib/candleTransform（可測）；本元件只管 chart 生命週期 + 主題色解析。
 * jsdom 無 canvas → 測試 mock 'lightweight-charts'，不在測試渲染真圖（見 GOAL / testing 規範）。
 */
import { useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
} from 'lightweight-charts'
import type { RunCandle, RunMarker } from '../api/candles'
import { toCandlestickData, toSeriesMarkers } from '../lib/candleTransform'

/** 讀已解析的 CSS token 值（canvas 無法吃 var()）；jsdom 空值時退回品牌 fallback。 */
function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

export interface CandlestickChartProps {
  candles: RunCandle[]
  markers: RunMarker[]
  height?: number
}

export function CandlestickChart({ candles, markers, height = 420 }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const gain = cssVar('--gain', '#22c55e')
    const loss = cssVar('--loss', '#f87171')
    const surface = cssVar('--bg-surface', '#1a1a1a')
    const border = cssVar('--border-default', '#2a2a2a')
    const muted = cssVar('--text-muted', 'rgba(245,245,245,0.55)')

    const chart = createChart(el, {
      height,
      width: el.clientWidth,
      layout: {
        background: { type: ColorType.Solid, color: surface },
        textColor: muted,
        fontFamily: 'Geist Mono, ui-monospace, monospace',
      },
      grid: { vertLines: { color: border }, horzLines: { color: border } },
      rightPriceScale: { borderColor: border },
      timeScale: { borderColor: border, timeVisible: false },
      crosshair: { mode: 0 },
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor: gain,
      downColor: loss,
      borderUpColor: gain,
      borderDownColor: loss,
      wickUpColor: gain,
      wickDownColor: loss,
    })
    series.setData(toCandlestickData(candles))
    createSeriesMarkers(series, toSeriesMarkers(markers, { gain, loss }))
    chart.timeScale().fitContent()

    const onResize = () => chart.applyOptions({ width: el.clientWidth })
    window.addEventListener('resize', onResize)

    return () => {
      window.removeEventListener('resize', onResize)
      chart.remove()
    }
  }, [candles, markers, height])

  return (
    <div
      ref={containerRef}
      data-testid="candlestick-chart"
      style={{ width: '100%', height }}
      role="img"
      aria-label="個股 K 線圖，疊進出場 marker"
    />
  )
}
