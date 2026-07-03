/*
 * 逐筆覆盤（/research/runs/:id/trades）— 後端 8.H.3 / S4。
 * 接真實 GET /runs/{id}/candles（個股 K 線 + 進出場 marker，ADR-034 lightweight-charts）
 * + /runs/{id}/trades（逐筆）+ /runs/{id}/equity（曲線摘要）。run 未持久化 series
 * 或該股無 parquet 時，端點回 typed-empty pending → 顯示空狀態（GOAL #8：不假造）。
 * 因子歸因（attribution）端點仍 needs-work → pending note。
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation('research')
  const { id } = useParams<{ id: string }>()
  const runId = id ?? ''
  const [selectedSymbol, setSelectedSymbol] = useState<string | undefined>(undefined)

  const candlesQ = useRunCandles(runId, selectedSymbol)
  const tradesQ = useRunTrades(runId)
  const equityQ = useRunEquity(runId)

  const candlesRes = candlesQ.data
  const candles = candlesRes?.data?.candles ?? []
  const markers = candlesRes?.data?.markers ?? []
  const symbols = candlesRes?.data?.symbols ?? []
  const activeSymbol = candlesRes?.data?.symbol ?? null
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
        title={t('trades.title')}
        route={`/research/runs/${runId}/trades`}
        subtitle={t('trades.subtitle')}
        back={{ label: t('trades.back'), to: `/research/runs/${runId}` }}
      />

      {/* candlestick — 個股 K 線 + entry ▲ / exit ▼ marker */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <h2 className="text-[18px] font-semibold">{t('trades.candles.title')}</h2>
          {symbols.length >= 2 && (
            <label className="flex items-center gap-1.5 text-xs text-text-muted">
              {t('trades.candles.symbolLabel')}
              <select
                className="rounded-md border border-border bg-code px-2 py-1 font-mono text-text focus:outline-none focus:ring-2 focus:ring-white/80"
                value={activeSymbol ?? ''}
                onChange={(e) => setSelectedSymbol(e.target.value)}
              >
                {symbols.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          )}
          {markers.length > 0 && (
            <span className="flex items-center gap-3 text-xs text-text-muted">
              <span className="text-gain">▲ {t('trades.candles.entry')}</span>
              <span className="text-loss">▼ {t('trades.candles.exit')}</span>
            </span>
          )}
        </div>
        {candlesQ.isLoading ? (
          <SkeletonRows rows={6} cols={1} />
        ) : candlesQ.isError ? (
          <p className="text-sm text-loss">{t('trades.candles.loadError')}</p>
        ) : candlesPending ? (
          <p className="text-sm text-text-muted">{t('trades.candles.empty')}</p>
        ) : (
          <CandlestickChart candles={candles} markers={markers} />
        )}
      </section>

      {/* equity summary */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-2 text-[18px] font-semibold">{t('trades.equity.title')}</h2>
        {equityQ.isLoading ? (
          <SkeletonRows rows={1} cols={3} />
        ) : equity.length === 0 ? (
          <p className="text-sm text-text-muted">{t('trades.equity.empty')}</p>
        ) : (
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <div className="text-xs text-text-muted">{t('trades.equity.final')}</div>
              <div className="font-mono tabular text-text">{finalEquity?.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-xs text-text-muted">{t('trades.equity.maxdd')}</div>
              <div className="font-mono tabular text-loss">{maxDrawdown !== null ? pct(maxDrawdown) : '—'}</div>
            </div>
            <div>
              <div className="text-xs text-text-muted">{t('trades.equity.bars')}</div>
              <div className="font-mono tabular text-text">{equity.length}</div>
            </div>
          </div>
        )}
      </section>

      {/* trades table */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">{t('trades.trades.title')}</h2>
          {trades.length > 0 && (
            <span className="text-xs text-text-muted">
              {t('trades.trades.summary', { n: trades.length, winRate: pct(wins / trades.length) })}
            </span>
          )}
        </div>
        {tradesQ.isLoading ? (
          <SkeletonRows rows={5} cols={4} />
        ) : trades.length === 0 ? (
          <p className="text-sm text-text-muted">{t('trades.trades.empty')}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="py-1.5 pr-3 font-medium">#</th>
                <th className="py-1.5 pr-3 font-medium">{t('trades.trades.ret')}</th>
                <th className="py-1.5 pr-3 font-medium">{t('trades.trades.hold')}</th>
                <th className="py-1.5 pr-3 font-medium">{t('trades.trades.entryStructure')}</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((tr, i) => (
                <tr key={i} className="border-b border-border/40">
                  <td className="py-1.5 pr-3 font-mono tabular text-text-muted">{i + 1}</td>
                  <td className="py-1.5 pr-3">
                    <StatusBadge tone={tr.ret > 0 ? 'gain' : 'loss'}>{pct(tr.ret)}</StatusBadge>
                  </td>
                  <td className="py-1.5 pr-3 font-mono tabular text-text">{tr.hold}</td>
                  <td className="py-1.5 pr-3 font-mono tabular text-text-secondary">{tr.entry_structure}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* still needs-work endpoint */}
      <div className="flex flex-col gap-2">
        <PendingNote label={t('trades.pending.attribution')} />
      </div>
    </div>
  )
}
