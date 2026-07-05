/*
 * useRuns — Runs Table 的 server-state hook（TanStack Query + envelope client）。
 * TTL 由 meta.ttl 驅動（doc 25 §5：research 區建議 300s）。
 */
import { useQuery } from '@tanstack/react-query'
import { listRuns } from '../api/runs'
import { ttlToMs } from '@/services/queryClient'

export function useRuns(params?: { strategy_id?: string; status?: string; page?: number; limit?: number }) {
  return useQuery({
    queryKey: ['runs', params ?? {}],
    queryFn: async () => {
      const res = await listRuns(params)
      return res
    },
    // research 區預設 300s（meta.ttl 若有則覆寫 staleTime）
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
