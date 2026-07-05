/*
 * Live-OOS 佇列 server-state hook（Goal 10，fixture-first）。
 * 打 GET /research/live-oos/queue；失敗 fallback 打包 fixture（見 api/queue.fetchLiveOosQueue）。
 * 佇列唯讀（消費在後端 after-close tick，ADR-040）→ 本 hook 只負責 items + source。
 */
import { useQuery } from '@tanstack/react-query'
import { ttlToMs } from '@/services/queryClient'
import { fetchLiveOosQueue, type LiveOosQueueResult } from '../api/queue'

export const LIVE_OOS_QUEUE_KEY = ['live-oos', 'queue'] as const

export function useLiveOosQueue() {
  return useQuery<LiveOosQueueResult>({
    queryKey: LIVE_OOS_QUEUE_KEY,
    queryFn: fetchLiveOosQueue,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
