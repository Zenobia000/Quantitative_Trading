/* usePromote* — promotion state machine（後端 8.H.7 / S3）。 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { advancePromote, getPromoteAudit, getPromoteState } from '../api/promote'
import { ttlToMs } from '@/services/queryClient'

export function usePromoteState(strategyId: string | undefined) {
  return useQuery({
    queryKey: ['promote-state', strategyId],
    queryFn: () => getPromoteState(strategyId as string),
    enabled: !!strategyId,
    staleTime: ttlToMs(300, 300),
  })
}

export function usePromoteAudit(strategyId: string | undefined) {
  return useQuery({
    queryKey: ['promote-audit', strategyId],
    queryFn: () => getPromoteAudit(strategyId as string),
    enabled: !!strategyId,
    staleTime: ttlToMs(300, 300),
  })
}

/** 前進一階（draft→paper→live）；成功後 invalidate state + audit。 */
export function useAdvancePromote(strategyId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { to_stage: string; note?: string; actor?: string }) =>
      advancePromote(strategyId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['promote-state', strategyId] })
      qc.invalidateQueries({ queryKey: ['promote-audit', strategyId] })
    },
  })
}
