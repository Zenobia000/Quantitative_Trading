/* useRun — 單一 run（GET /runs/{id}，shipped）。 */
import { useQuery } from '@tanstack/react-query'
import { getRun } from '../api/runs'
import { ttlToMs } from '@/services/queryClient'

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId as string),
    enabled: !!runId,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
