/* useSweep — async sweep job 提交 + 輪詢（後端 8.H.6 / S2）。 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { getSweepStatus, submitSweep } from '../api/sweep'

/** 提交 grid → {job_id, status:'queued'}。呼叫端拿 job_id 後用 useSweepStatus 輪詢。 */
export function useSubmitSweep() {
  return useMutation({
    mutationFn: (grid: Record<string, unknown[]>) => submitSweep(grid),
  })
}

/** 輪詢 job 狀態；done/failed 前每秒 refetch（doc 25 §5：job 輪詢）。 */
export function useSweepStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: ['sweep-status', jobId],
    queryFn: () => getSweepStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.data?.status
      return status === 'done' || status === 'failed' ? false : 1000
    },
  })
}
