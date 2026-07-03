/*
 * Research zone — 個股 K 線 + 進出場 marker（GET /runs/{id}/candles，後端 S4）。
 * 讀 parquet OHLC + 由 run 訊號管線重推的 entry/exit marker；未持久化該股 →
 * meta.data_source=pending（前端渲染空態，不假造，GOAL.md #8）。
 * 後端 response_model 為泛型 Envelope，故 data 形狀以手寫 view-model 承載（同 series.ts）。
 */
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

/** 一根日 K（lightweight-charts 消費形狀：business-day 'YYYY-MM-DD' time）。 */
export interface RunCandle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

/** 一個進出場 marker（entry ▲ / exit ▼），price=成交價，ret=該筆報酬（僅 exit）。 */
export interface RunMarker {
  time: string
  kind: 'entry' | 'exit'
  price: number
  ret?: number
}

export interface RunCandles {
  run_id: string
  /** 目前作圖的個股 stock_id（無交易個股時為 null；doc 25 §1.3 canonical id）。 */
  stock_id: string | null
  /** 該 run 有交易的 stock_id 清單（驅動個股 selector）。 */
  stock_ids: string[]
  candles: RunCandle[]
  markers: RunMarker[]
}

/** GET /runs/{id}/candles — 個股 K 線 + 進出場 marker（可選 ?stock_id= 指定個股，A5 canonical id）。 */
export function getRunCandles(runId: string, stockId?: string): Promise<ApiResult<RunCandles>> {
  return http<RunCandles>(`/runs/${encodeURIComponent(runId)}/candles`, { query: { stock_id: stockId } })
}
