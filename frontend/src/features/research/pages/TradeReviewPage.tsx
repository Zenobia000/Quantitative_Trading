/*
 * 逐筆覆盤（/research/runs/:id/trades）— 後端 8.H.3 / S4。
 * 接真實 GET /runs/{id}/candles（個股 K 線 + 進出場 marker，ADR-034 lightweight-charts）
 * + /runs/{id}/trades（逐筆）+ /runs/{id}/equity（曲線摘要）。run 未持久化 series
 * 或該股無 parquet 時，端點回 typed-empty pending → 顯示空狀態（GOAL #8：不假造）。
 * 因子歸因（attribution）端點仍 needs-work → pending note。
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useRunEquity, useRunTrades } from '../hooks/useRunSeries'
import { useRunCandles } from '../hooks/useRunCandles'
import { CandlestickChart } from '../components/CandlestickChart'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { isPending } from '@/types/domain'

function pct(x: number): string {
  return `${(x * 100).toFixed(2)}%`
}

export function TradeReviewPage() {
  const { id } = useParams<{ id: string }>()
  const runId = id ?? ''
  const [selectedStockId, setSelectedStockId] = useState<string | undefined>(undefined)

  const candlesQ = useRunCandles(runId, selectedStockId)
  const tradesQ = useRunTrades(runId)
  const equityQ = useRunEquity(runId)

  const candlesRes = candlesQ.data
  const candles = candlesRes?.data?.candles ?? []
  const markers = candlesRes?.data?.markers ?? []
  const stockIds = candlesRes?.data?.stock_ids ?? []
  const activeStockId = candlesRes?.data?.stock_id ?? null
  const candlesPending = isPending(candlesRes?.meta) || candles.length === 0

  const trades = tradesQ.data?.data?.trades ?? []
  const equity = equityQ.data?.data?.equity ?? []
  const drawdown = equityQ.data?.data?.drawdown ?? []
  const finalEquity = equity.length ? equity[equity.length - 1] : null
  const maxDrawdown = drawdown.length ? Math.min(...drawdown) : null
  const wins = trades.filter((t) => t.ret > 0).length

  return (
    <div>
      <PageHeader
        title="逐筆覆盤"
        route={`/research/runs/${runId}/trades`}
        subtitle="個股 K 線 + 進出場 marker · 逐筆交易 · 權益曲線摘要（GET /runs/{id}/candles · /trades · /equity）"
      />

      {/* candlestick — 個股 K 線 + entry ▲ / exit ▼ marker */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <h2 className="text-[18px] font-semibold">個股 K 線</h2>
          {stockIds.length >= 2 && (
            <label className="flex items-center gap-1.5 text-xs text-text-muted">
              標的
              <select
                className="rounded-md border border-border bg-code px-2 py-1 font-mono text-text focus:outline-none focus:ring-2 focus:ring-white/80"
                value={activeStockId ?? ''}
                onChange={(e) => setSelectedStockId(e.target.value)}
              >
                {stockIds.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          )}
          {markers.length > 0 && (
            <span className="flex items-center gap-3 text-xs text-text-muted">
              <span className="text-gain">▲ 進場</span>
              <span className="text-loss">▼ 出場</span>
            </span>
          )}
        </div>
        {candlesQ.isLoading ? (
          <SkeletonRows rows={6} cols={1} />
        ) : candlesQ.isError ? (
          <p className="text-sm text-loss">K 線載入失敗，請重試。</p>
        ) : candlesPending ? (
          <p className="text-sm text-text-muted">
            此個股尚無 K 線資料（parquet 快取未涵蓋該標的或此 run 無交易個股）。
          </p>
        ) : (
          <CandlestickChart candles={candles} markers={markers} />
        )}
      </section>

      {/* equity summary */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-2 text-[18px] font-semibold">權益摘要</h2>
        {equityQ.isLoading ? (
          <SkeletonRows rows={1} cols={3} />
        ) : equity.length === 0 ? (
          <p className="text-sm text-text-muted">此 run 尚無持久化權益序列（舊 run 或無交易窗）。</p>
        ) : (
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <div className="text-xs text-text-muted">期末權益（起始 1.0）</div>
              <div className="font-mono tabular text-text">{finalEquity?.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-xs text-text-muted">最大回撤</div>
              <div className="font-mono tabular text-loss">{maxDrawdown !== null ? pct(maxDrawdown) : '—'}</div>
            </div>
            <div>
              <div className="text-xs text-text-muted">bar 數</div>
              <div className="font-mono tabular text-text">{equity.length}</div>
            </div>
          </div>
        )}
      </section>

      {/* trades table */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">逐筆交易</h2>
          {trades.length > 0 && (
            <span className="text-xs text-text-muted">
              {trades.length} 筆 · 勝率 {pct(wins / trades.length)}
            </span>
          )}
        </div>
        {tradesQ.isLoading ? (
          <SkeletonRows rows={5} cols={4} />
        ) : trades.length === 0 ? (
          <p className="text-sm text-text-muted">此 run 尚無逐筆交易紀錄。</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="py-1.5 pr-3 font-medium">#</th>
                <th className="py-1.5 pr-3 font-medium">報酬</th>
                <th className="py-1.5 pr-3 font-medium">持有 (bar)</th>
                <th className="py-1.5 pr-3 font-medium">進場 structure</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t, i) => (
                <tr key={i} className="border-b border-border/40">
                  <td className="py-1.5 pr-3 font-mono tabular text-text-muted">{i + 1}</td>
                  <td className="py-1.5 pr-3">
                    <StatusBadge tone={t.ret > 0 ? 'gain' : 'loss'}>{pct(t.ret)}</StatusBadge>
                  </td>
                  <td className="py-1.5 pr-3 font-mono tabular text-text">{t.hold}</td>
                  <td className="py-1.5 pr-3 font-mono tabular text-text-secondary">{t.entry_structure}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* still needs-work endpoint */}
      <div className="flex flex-col gap-2">
        <PendingNote label="因子歸因（/runs/{id}/attribution 待後端）" />
      </div>
    </div>
  )
}
