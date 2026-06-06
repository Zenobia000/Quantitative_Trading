/* Promote（/research/promote/:strategyId）— 接 /research/promote/{id}（typed stub，狀態機 M3.6）。 */
import { useParams } from 'react-router-dom'
import { WiredPage } from '@/components/WiredPage'

export function PromotePage() {
  const { strategyId } = useParams<{ strategyId: string }>()
  return (
    <WiredPage
      title="Promotion stepper"
      route={`/research/promote/${strategyId}`}
      spec="research_08_promote"
      endpoint={strategyId ? `/research/promote/${encodeURIComponent(strategyId)}` : null}
      subtitle="不可逆晉升狀態機（持久化 M3.6）；端點已接線回 typed-empty"
    />
  )
}
