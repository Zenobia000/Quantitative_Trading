/* useGateState — validation gate-state（後端 8.H.7 / S3）。 */
import { useQuery } from '@tanstack/react-query'
import { getGateState } from '../api/validateGate'
import { ttlToMs } from '@/services/queryClient'

export function useGateState(runId: string | undefined) {
  return useQuery({
    queryKey: ['gate-state', runId],
    queryFn: () => getGateState(runId as string),
    enabled: !!runId,
    staleTime: ttlToMs(300, 300),
  })
}
