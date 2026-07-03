/*
 * Candidate 決策 mutation hooks（api 模式真寫入）——共用給 Candidate Pool 與 Report Viewer。
 * 成功後 invalidate CANDIDATES_KEY → 重抓折疊後的候選池（server truth，不做本地拼接）。
 * 失敗（400 illegal transition / 422 缺 reason / 409 blocked）由呼叫端 onError 呈現，不靜默。
 * fixture 模式不經此路徑（頁面以本地樂觀 overlay 承接）。
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  postCandidateDecision,
  postSelectLiveOos,
  type CandidateDecision,
  type DecisionRequestBody,
  type LiveOosQueueItem,
  type SelectLiveOosRequestBody,
} from '../api/candidates'
import { CANDIDATES_KEY } from './useCandidatePool'

export interface DecisionMutationVars {
  candidateId: string
  body: DecisionRequestBody
}

export interface SelectLiveOosMutationVars {
  candidateId: string
  body: SelectLiveOosRequestBody
}

/** keep / archive / rerun / mark_data_issue / unarchive → POST /decision，成功後重抓候選池。 */
export function useDecisionMutation() {
  const qc = useQueryClient()
  return useMutation<CandidateDecision, unknown, DecisionMutationVars>({
    mutationFn: ({ candidateId, body }) => postCandidateDecision(candidateId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CANDIDATES_KEY })
    },
  })
}

/** select_live_oos / override_select → POST /select-live-oos，成功後重抓候選池。 */
export function useSelectLiveOosMutation() {
  const qc = useQueryClient()
  return useMutation<LiveOosQueueItem, unknown, SelectLiveOosMutationVars>({
    mutationFn: ({ candidateId, body }) => postSelectLiveOos(candidateId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CANDIDATES_KEY })
    },
  })
}
