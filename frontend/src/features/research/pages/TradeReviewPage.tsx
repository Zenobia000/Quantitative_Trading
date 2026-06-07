/*
 * 逐筆覆盤（/research/runs/:id/trades）— 後端 8.H.3 / S4。
 * 接真實 GET /runs/{id}/trades（逐筆）+ /runs/{id}/equity（曲線摘要）。run 未持久化
 * series（舊 run / 無交易）時端點回 typed-empty pending → 顯示空狀態。
 * 個股 K 線 + 因子歸因（candles / attribution）端點仍 needs-work → pending note。
 */
import { useParams } from 'react-router-dom'
import { useRunEquity, useRunTrades } from '../hooks/useRunSeries'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'

function pct(x: number): string {
  return `${(x * 100).toFixed(2)}%`
}

export function TradeReviewPage() {
  const { id } = useParams<{ id: string }>()
  const runId = id ?? ''
  const tradesQ = useRunTrades(runId)
  const equityQ = useRunEquity(runId)

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
        subtitle="逐筆交易 + 權益曲線摘要（GET /runs/{id}/trades · /equity）"
      />

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

      {/* still needs-work endpoints */}
      <div className="flex flex-col gap-2">
        <PendingNote label="個股 K 線 + 進出場 marker（/runs/{id}/candles 待後端）" />
        <PendingNote label="因子歸因（/runs/{id}/attribution 待後端）" />
      </div>
    </div>
  )
}
