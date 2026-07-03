/*
 * IA 遷移的 client-side 重導元件（rebuild IA §5.6）。
 * 純位置搬遷，零邏輯變更：舊 Research route → 新 Deployment route。
 * 照 #192 monitor/watch 前例（<Navigate replace />），但保留舊 URL 的上下文：
 *  - GateRedirect：帶著 search 一起搬（validate?run_id= → gate?run_id=），不丟失候選選取。
 *  - PromoteRedirect：轉發 :strategyId 路徑參數。
 */
import { Navigate, useLocation, useParams } from 'react-router-dom'

/** /research/validate(?run_id=…) → /deploy/gate(?run_id=…)（保留 query） */
export function GateRedirect() {
  const { search } = useLocation()
  return <Navigate to={`/deploy/gate${search}`} replace />
}

/** /research/promote/:strategyId → /deploy/promote/:strategyId（轉發參數） */
export function PromoteRedirect() {
  const { strategyId } = useParams()
  return <Navigate to={`/deploy/promote/${encodeURIComponent(strategyId ?? '')}`} replace />
}
