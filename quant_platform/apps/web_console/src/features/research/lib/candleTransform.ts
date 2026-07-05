/*
 * API → lightweight-charts 形狀的純轉換（無 canvas / DOM，可在 jsdom 單元測試）。
 * 圖表元件把 API 形狀交給這裡轉，元件本身只管 chart 生命週期。
 * lightweight-charts 僅以 `import type` 引入（編譯期抹除，測試不載入 canvas lib）。
 */
import type { CandlestickData, SeriesMarker, Time } from 'lightweight-charts'
import type { RunCandle, RunMarker } from '../api/candles'

/** 漲跌雙編碼用色（由呼叫端傳入已解析的 theme token 值，純函式不碰 DOM）。 */
export interface MarkerColors {
  gain: string
  loss: string
}

/** OHLC candle → CandlestickData（'YYYY-MM-DD' 直接作 business-day time）。 */
export function toCandlestickData(candles: RunCandle[]): CandlestickData<Time>[] {
  return candles.map((c) => ({
    time: c.time as Time,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }))
}

function pct(x: number): string {
  return `${(x * 100).toFixed(1)}%`
}

/**
 * 進出場 marker → SeriesMarker：
 * - entry：belowBar + ▲（arrowUp），gain 色，標進場價（漲跌 + 符號雙編碼）。
 * - exit ：aboveBar + ▼（arrowDown），依該筆 ret 取 gain/loss 色，標報酬 %。
 * 依 time 升冪（後端已成對輸出）— createSeriesMarkers 要求升冪。
 */
export function toSeriesMarkers(markers: RunMarker[], colors: MarkerColors): SeriesMarker<Time>[] {
  return markers.map((m) => {
    if (m.kind === 'entry') {
      return {
        time: m.time as Time,
        position: 'belowBar',
        shape: 'arrowUp',
        color: colors.gain,
        text: `進 ${m.price.toFixed(2)}`,
      }
    }
    const up = (m.ret ?? 0) >= 0
    return {
      time: m.time as Time,
      position: 'aboveBar',
      shape: 'arrowDown',
      color: up ? colors.gain : colors.loss,
      text: m.ret === undefined ? '出' : `出 ${pct(m.ret)}`,
    }
  })
}
