/*
 * Paper-Watch 觀察艙 server-state hooks (ADR-033 GUI补).
 * GET /monitor/watch → 每個艙位狀態 + timer 健康度 + 最近 session 時間線；
 * POST /monitor/watch/{strategy}/pause|resume → app 層暫停/恢復（成功後 refetch overview）。
 * 形狀為手寫 view-model（後端 /monitor/watch 回無型別 Envelope，同 useMonitor.ts 慣例）。
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { http } from '@/services/http'
import { useEndpoint } from '@/hooks/useEndpoint'
import type { ApiResult } from '@/types/domain'

export type TimerHealth = 'ok' | 'stale' | 'never_ran'
export type WatchState = 'active' | 'paused' | 'expired' | 'exited'

export interface WatchSession {
  date: string
  /** OK | FAILED | NO_DATA | SKIP（today markers 僅記成功 → 多為 OK；badge 支援其餘態） */
  status: string
}

export interface WatchRow {
  strategy: string
  status: WatchState
  enrolled_on: string
  verdict_dsr: number
  observed_trading_days: number
  nominal_trading_days: number
  expiry_date: string
  days_remaining: number
  timer_health: TimerHealth
  last_session_date: string | null
  last_session_at: string | null
  last_trading_day: string
  sessions: WatchSession[]
}

/** 觀察艙清單的共用 query key（對齊 useEndpoint 慣例，供 mutation invalidate）。 */
export const WATCH_KEY = ['endpoint', '/monitor/watch'] as const

export const useWatchOverview = () => useEndpoint<WatchRow[]>('/monitor/watch', 60)

/** 暫停 / 恢復一個艙位；成功後 invalidate overview（refetch 反映新狀態）。 */
export function useWatchToggle() {
  const qc = useQueryClient()
  return useMutation<ApiResult<WatchRow>, Error, { strategy: string; action: 'pause' | 'resume' }>({
    mutationFn: ({ strategy, action }) =>
      http<WatchRow>(`/monitor/watch/${encodeURIComponent(strategy)}/${action}`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCH_KEY }),
  })
}
