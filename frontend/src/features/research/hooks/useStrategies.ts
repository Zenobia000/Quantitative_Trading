/* useStrategies — 策略 roster（GET /research/strategies，shipped）。 */
import { useQuery } from '@tanstack/react-query'
import { listStrategies } from '../api/strategies'
import { ttlToMs } from '@/services/queryClient'

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => listStrategies(),
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
