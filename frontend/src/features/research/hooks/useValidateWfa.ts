/* useValidateWfa — WFA folds（後端 6.2.2 / S7）。 */
import { useQuery } from '@tanstack/react-query'
import { getValidateWfa } from '../api/wfa'
import { ttlToMs } from '@/services/queryClient'

export function useValidateWfa(runId: string | undefined) {
  return useQuery({
    queryKey: ['validate-wfa', runId],
    queryFn: () => getValidateWfa(runId as string),
    enabled: !!runId,
    staleTime: ttlToMs(300, 300),
  })
}
