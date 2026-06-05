/* 逐筆覆盤（/research/runs/:id/trades）— candles/trades/attribution 端點 needs-work（M3）→ 結構 pending。 */
import { useParams } from 'react-router-dom'
import { WiredPage } from '@/components/WiredPage'

export function TradeReviewPage() {
  const { id } = useParams<{ id: string }>()
  return (
    <WiredPage
      title="逐筆覆盤"
      route={`/research/runs/${id}/trades`}
      spec="research_trade_review"
      endpoint={null}
      subtitle="個股 K 線 + 進出場 marker + 因子歸因（/runs/{id}/candles·trades·attribution 待後端 M3）"
    />
  )
}
