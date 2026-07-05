/*
 * Branch experiments hooks（Goal 9）—— 列該策略的分支 + create/evaluate mutation。
 * 成功後 invalidate BRANCHES_KEY → 重抓折疊後的分支清單（server truth，不本地拼接）。
 * 錯誤（404/409/422）由呼叫端 onError 呈現（不靜默）。
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createBranch,
  evaluateBranch,
  fetchBranchCompare,
  fetchBranches,
  type BranchCompare,
  type BranchExperiment,
  type CreateBranchBody,
} from '../api/branches'

export const BRANCHES_KEY = ['research', 'branches'] as const

/** 列某策略的分支（strategy 未定義時停用查詢）。 */
export function useBranches(strategy: string | undefined) {
  return useQuery<BranchExperiment[]>({
    queryKey: [...BRANCHES_KEY, strategy ?? ''],
    queryFn: () => fetchBranches({ strategy }),
    enabled: !!strategy,
    staleTime: 60_000,
  })
}

/** Fork 分支 → 成功後重抓分支清單。 */
export function useCreateBranch() {
  const qc = useQueryClient()
  return useMutation<BranchExperiment, unknown, CreateBranchBody>({
    mutationFn: (body) => createBranch(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BRANCHES_KEY })
    },
  })
}

/** 評測分支 → 成功後重抓分支清單（回填 evaluation_id 反映到列表 status）。 */
export function useEvaluateBranch() {
  const qc = useQueryClient()
  return useMutation<BranchExperiment, unknown, string>({
    mutationFn: (branchId) => evaluateBranch(branchId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BRANCHES_KEY })
    },
  })
}

/** 分支 vs parent compare delta 表（僅在展開時抓，enabled 由呼叫端控制）。 */
export function useBranchCompare(branchId: string, enabled: boolean) {
  return useQuery<BranchCompare>({
    queryKey: [...BRANCHES_KEY, branchId, 'compare'],
    queryFn: () => fetchBranchCompare(branchId),
    enabled,
    staleTime: 60_000,
  })
}
