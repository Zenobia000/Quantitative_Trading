/* useValidateHealth — 13 指標健康表（後端 6.1.3 / v2.md §4.3.1）。 */
import { useQuery } from '@tanstack/react-query'
import { getValidateHealth } from '../api/health'
import { ttlToMs } from '@/services/queryClient'

export function useValidateHealth(runId: string | undefined) {
  return useQuery({
    queryKey: ['validate-health', runId],
    queryFn: () => getValidateHealth(runId as string),
    enabled: !!runId,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
