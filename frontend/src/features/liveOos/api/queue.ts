/*
 * Governance OOS queue（fixture-first）。
 * 先打 `GET /research/live-oos/queue`（envelope client，#188 已上線真後端）；
 * 任何 ApiError（404 / NETWORK / 後端錯誤）fallback 到打包契約範例 `../fixtures/live_oos_queue.json`，
 * 並回傳 source 供 UI 明示資料來源（fixture 模式 banner）。
 *
 * 型別為手寫窄化 view-model（對齊 dev_docs/contracts/live_oos_queue.example.json），不碰 api.gen.ts。
 * 佇列為唯讀決策證據面：消費（enroll/replay/狀態推進）在後端 after-close tick 進行（ADR-040），前端不寫。
 */
import { http, ApiError } from '@/services/http'
import type { ApiMeta } from '@/types/domain'
import fixture from '../fixtures/live_oos_queue.json'

/** 佇列折疊態（contract §7；registry active→running / paused / expired / exited→completed + 佇列專屬 queued/cancelled）。 */
export type QueueState = 'queued' | 'running' | 'paused' | 'completed' | 'expired' | 'cancelled'

/** 觀察型別：berth（watch_registry 1:1）/ 一次性 paper replay / after-close 排程 session。 */
export type ObservationKind = 'paper_watch_berth' | 'paper_replay' | 'after_close'

/** 勾選當下的 live-OOS 建議（audit：override 標記據此）。 */
export type Recommendation = 'eligible' | 'not_recommended' | 'blocked'

export interface QueueObservation {
  kind: ObservationKind
  watch_registry_ref: string | null
  dsr_band: string | null
  verdict_dsr: number | null
  enrolled_on: string | null
  expiry_date: string | null
  observation_days: number | null
  observed_trading_days: number | null
  days_remaining: number | null
  position_size: number
}

/** paper_replay 完成後回填的執行結果（consumer 附）。 */
export interface QueueRun {
  run_id: string | null
  gate_status: string | null
  ran_at?: string
}

/** 佇列項連回三處的 API 路徑字串（契約以 "GET /research/..." 形式存；UI route 另行推導）。 */
export interface QueueLinks {
  report: string
  candidate: string
  strategy_asset: string
}

export interface LiveOosQueueItem {
  queue_id: string
  candidate_id: string
  strategy: string
  evaluation_id: string
  selected_at: string
  selected_by: string
  selection_reason: string | null
  recommendation_at_selection: Recommendation
  override: boolean
  override_reason?: string | null
  state: QueueState
  observation: QueueObservation
  run?: QueueRun
  report_pack_ref: string | null
  links: QueueLinks
}

export type QueueSource = 'api' | 'fixture'

export interface LiveOosQueueResult {
  items: LiveOosQueueItem[]
  meta: ApiMeta
  /** 'api' = 後端 live；'fixture' = 打包契約範例（示範模式）。 */
  source: QueueSource
}

interface QueueEnvelopeShape {
  data: LiveOosQueueItem[]
  meta: ApiMeta
}

/**
 * 抓 live-OOS 佇列：先打後端，失敗即 fallback 打包 fixture。
 * 回傳 `source` 讓 UI 明示資料來源（fixture 模式 badge）。
 */
export async function fetchLiveOosQueue(): Promise<LiveOosQueueResult> {
  try {
    const res = await http<LiveOosQueueItem[]>('/research/live-oos/queue')
    return { items: res.data ?? [], meta: res.meta, source: 'api' }
  } catch (e) {
    // 非 ApiError（非預期）才向上拋；ApiError → 打包契約範例（示範模式）。
    if (!(e instanceof ApiError)) throw e
    const env = fixture as unknown as QueueEnvelopeShape
    return { items: env.data, meta: { ...env.meta, data_source: 'fixture' }, source: 'fixture' }
  }
}
