/* useStrategyRegistry — 策略型錄（GET /strategies，shipped，ADR-028）。 */
import { useQuery } from '@tanstack/react-query'
import { listStrategyRegistry } from '../api/registry'

export function useStrategyRegistry() {
  return useQuery({
    queryKey: ['strategy-registry'],
    queryFn: listStrategyRegistry,
    staleTime: 10 * 60_000, // 型錄低頻變動
  })
}
