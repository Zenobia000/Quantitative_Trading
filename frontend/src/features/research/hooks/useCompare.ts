/* useCompare — 跨 run 比較（GET /runs/compare，shipped）。 */
import { useQuery } from '@tanstack/react-query'
import { getCompare } from '../api/compare'
import { ttlToMs } from '@/services/queryClient'

export function useCompare(baseline?: string, enabled = true) {
  return useQuery({
    queryKey: ['compare', baseline ?? null],
    queryFn: () => getCompare(baseline),
    enabled,
    staleTime: ttlToMs(300, 300),
  })
}
