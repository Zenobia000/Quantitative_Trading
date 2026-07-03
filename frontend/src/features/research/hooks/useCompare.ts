/* useCompare — 跨 run 比較（GET /runs/compare，shipped）。 */
import { useQuery } from '@tanstack/react-query'
import { getCompare } from '../api/compare'
import { ttlToMs } from '@/services/queryClient'

export function useCompare(baseline?: string, runIds: string[] = [], enabled = true) {
  return useQuery({
    queryKey: ['compare', baseline ?? null, runIds],
    queryFn: () => getCompare({ baseline, run_ids: runIds }),
    enabled,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
