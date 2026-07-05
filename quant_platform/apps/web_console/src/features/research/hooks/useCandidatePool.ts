/*
 * Candidate Pool server-state hook（Goal 6，fixture-first）。
 * 打 GET /research/candidates；失敗 fallback 打包 fixture（見 api/candidates.fetchCandidatePool）。
 * 決策為 fixture 模式本地樂觀更新 → 由頁面持有本地 overlay，本 hook 只負責 base 資料 + source。
 */
import { useQuery } from '@tanstack/react-query'
import { ttlToMs } from '@/services/queryClient'
import { fetchCandidatePool, type CandidatePoolResult } from '../api/candidates'

export const CANDIDATES_KEY = ['research', 'candidates'] as const

export function useCandidatePool() {
  return useQuery<CandidatePoolResult>({
    queryKey: CANDIDATES_KEY,
    queryFn: fetchCandidatePool,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
