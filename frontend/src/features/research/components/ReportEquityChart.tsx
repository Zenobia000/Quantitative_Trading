/*
 * 分段權益曲線 + 回撤（TradingView lightweight-charts v5，ADR-034；沿用 CandlestickChart 生命週期模式）。
 * 上 pane：權益線；下 pane：回撤面積（loss 色）。truth_gate_window.oos_start 有值時，
 * 在該日畫「sealed」marker 標注封存邊界（真偽閘 OOS 起點）。
 *
 * v1 序列 sidecar 不存日期索引 → x 軸以 run_window.is_start 重建 business-day（近似，UI 揭露 basis），
 * 與後端 runs_report 同法，好讓 oos_start 對位。jsdom 無 canvas → 測試 mock lightweight-charts。
 */
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AreaSeries,
  ColorType,
  LineSeries,
  createChart,
  createSeriesMarkers,
} from 'lightweight-charts'
import type { SeriesMarker, Time } from 'lightweight-charts'
import { reconstructBusinessDays } from '../lib/reportViz'
import { useTheme } from '@/app/theme'

/** 讀已解析 CSS token（canvas 無法吃 var()）；jsdom 空值退回品牌 fallback。 */
function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

export interface ReportEquityChartProps {
  equity: number[]
  drawdown: number[]
  /** run_window.is_start（重建 x 軸錨點）；null → 退合成序列、不畫 oos。 */
  isStart: string | null
  /** truth_gate_window.oos_start（封存邊界）；null → 不標注。 */
  oosStart: string | null
  height?: number
}

export function ReportEquityChart({
  equity,
  drawdown,
  isStart,
  oosStart,
  height = 340,
}: ReportEquityChartProps) {
  const { t } = useTranslation('research')
  // 主題切換需重解析 canvas 顏色（canvas 吃解析值非 CSS var）。
  const { resolved } = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el || equity.length === 0) return

    const gain = cssVar('--gain', '#22c55e')
    const loss = cssVar('--loss', '#f87171')
    const surface = cssVar('--bg-surface', '#1a1a1a')
    const border = cssVar('--border-default', '#2a2a2a')
    const muted = cssVar('--text-muted', 'rgba(245,245,245,0.55)')

    // 無 is_start → 合成 business-day 序列（僅為有效時間軸；oos 對位無意義故略）。
    const anchor = isStart ?? '2000-01-03'
    const dates = reconstructBusinessDays(anchor, equity.length)

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

    const eqSeries = chart.addSeries(LineSeries, { color: gain, lineWidth: 2, priceLineVisible: false })
    eqSeries.setData(equity.map((v, i) => ({ time: dates[i] as Time, value: v })))

    if (drawdown.length > 0) {
      const ddSeries = chart.addSeries(
        AreaSeries,
        {
          lineColor: loss,
          topColor: `${loss}00`,
          bottomColor: `${loss}66`,
          lineWidth: 1,
          priceLineVisible: false,
        },
        1, // pane 1（下方回撤區）
      )
      ddSeries.setData(drawdown.map((v, i) => ({ time: dates[i] as Time, value: v })))
    }

    // 封存邊界：oos_start 落在重建軸內時，在權益線上標「sealed」marker。
    if (oosStart && isStart) {
      const markers: SeriesMarker<Time>[] = [
        {
          time: oosStart as Time,
          position: 'aboveBar',
          shape: 'arrowDown',
          color: muted,
          text: t('report.equity.sealed'),
        },
      ]
      createSeriesMarkers(eqSeries, markers)
    }

    chart.timeScale().fitContent()

    const onResize = () => chart.applyOptions({ width: el.clientWidth })
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      chart.remove()
    }
  }, [equity, drawdown, isStart, oosStart, height, resolved, t])

  return (
    <div
      ref={containerRef}
      data-testid="report-equity-chart"
      style={{ width: '100%', height }}
      role="img"
      aria-label={t('report.equity.aria')}
    />
  )
}
