/* useEvaluation — Report-Viewer 主資料（GET /research/evaluations/{id}，fixture-first fallback）。 */
import { useQuery } from '@tanstack/react-query'
import { getEvaluation } from '../api/reportViewer'
import { ttlToMs } from '@/services/queryClient'

export function useEvaluation(id: string | undefined) {
  return useQuery({
    queryKey: ['evaluation', id],
    queryFn: () => getEvaluation(id as string),
    enabled: !!id,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
