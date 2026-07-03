/* useRunReport — Run-Report 一次性聚合（GET /runs/{id}/report，shipped）。 */
import { useQuery } from '@tanstack/react-query'
import { getRunReport } from '../api/report'
import { ttlToMs } from '@/services/queryClient'

export function useRunReport(runId: string | undefined) {
  return useQuery({
    queryKey: ['run-report', runId],
    queryFn: () => getRunReport(runId as string),
    enabled: !!runId,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
