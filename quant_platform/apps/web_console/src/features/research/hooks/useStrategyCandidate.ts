/*
 * useStrategyCandidate — 策略資產 ↔ 候選池的橋接層（Goal 7）。
 * 打 `GET /research/candidates`（#188 已上線的真後端，envelope client）→ 全候選池。
 * 後端已上線，**不做 fixture fallback**（誠實空態）：某策略不在池中 → null，UI 呈現「尚未評估」。
 *
 * 型別註記：`/research/candidates` 在 api.gen.ts 只映射為泛型 Envelope（data 為 unknown），
 * 無強型別 Candidate output schema，故直接複用 api/candidates.ts 的手寫 view-model 型別
 * （read-only import；不改該檔）——與候選池頁、CandidateStateBadge / ScorecardLights 共用同一型別。
 */
import { useMemo } from 'react'
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { http } from '@/services/http'
import type { Candidate } from '../api/candidates'

/** 與候選池頁的 fixture-first 查詢（['research','candidates']）刻意不同 key —— 本 hook 走真後端、無 fixture。 */
export const STRATEGY_CANDIDATES_KEY = ['research', 'candidates', 'live'] as const

/** 抓完整候選池（策略軸 enrichment 的單一來源；list 與 detail 共用同一 react-query 快取）。 */
async function fetchCandidates(): Promise<Candidate[]> {
  const res = await http<Candidate[]>('/research/candidates')
  return res.data ?? []
}

/** 全候選池 server-state（後端已上線；查詢失敗即誠實 error，不 fallback fixture）。 */
export function useStrategyCandidates(): UseQueryResult<Candidate[]> {
  return useQuery<Candidate[]>({
    queryKey: STRATEGY_CANDIDATES_KEY,
    queryFn: fetchCandidates,
    staleTime: 300_000,
  })
}

/**
 * strategy → 最新 Candidate 映射。候選池為 newest-created first，故每策略取「先到者」(=最新)。
 * 純函式，可獨立單元測試（無 React / 無 i18n）。
 */
export function candidatesByStrategy(list: Candidate[] | undefined): Map<string, Candidate> {
  const map = new Map<string, Candidate>()
  for (const c of list ?? []) {
    if (!map.has(c.strategy)) map.set(c.strategy, c)
  }
  return map
}

/**
 * 單策略候選（詳情頁）：共用池查詢，client 端挑該策略最新候選。
 * 無候選 → null（誠實空態）。回傳 query 供頁面區分 loading / error / 無候選三態。
 */
export function useStrategyCandidate(strategyName: string | undefined): {
  query: UseQueryResult<Candidate[]>
  candidate: Candidate | null
} {
  const query = useStrategyCandidates()
  const candidate = useMemo<Candidate | null>(() => {
    if (!strategyName) return null
    return candidatesByStrategy(query.data).get(strategyName) ?? null
  }, [query.data, strategyName])
  return { query, candidate }
}
