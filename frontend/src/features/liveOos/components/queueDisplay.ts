/*
 * Live-OOS 佇列純顯示邏輯（無 React、無 i18n → 可獨立單元測試）。
 * tone 映射本地維護（本頁不碰 status.json / displayMap.ts；label 走 liveOos namespace）。
 * 色 + 文字雙編碼（硬約束 #6）：tone 撞色可接受，text label 一律另附。
 */
import type { ObservationKind, QueueState } from '../api/queue'

export type Tone = 'gain' | 'loss' | 'warning' | 'error' | 'muted'

/** 佇列狀態 → tone。running=進行中(gain)、paused/expired=需注意(warning)、completed/queued/cancelled=中性(muted)。 */
const QUEUE_STATE_TONE: Record<QueueState, Tone> = {
  queued: 'muted',
  running: 'gain',
  paused: 'warning',
  completed: 'muted',
  expired: 'warning',
  cancelled: 'muted',
}

export function queueStateTone(state: string): Tone {
  return QUEUE_STATE_TONE[state as QueueState] ?? 'muted'
}

/** 觀察型別 → tone（資訊 chip 用；berth=gain、replay=muted、after_close=muted）。 */
const KIND_TONE: Record<ObservationKind, Tone> = {
  paper_watch_berth: 'gain',
  paper_replay: 'muted',
  after_close: 'muted',
}

export function kindTone(kind: string): Tone {
  return KIND_TONE[kind as ObservationKind] ?? 'muted'
}

/** berth 型（有觀察窗進度 + 到期倒數）；replay 是一次性批次，無觀察窗。 */
export function isBerthKind(kind: string): boolean {
  return kind === 'paper_watch_berth' || kind === 'after_close'
}

/** report_pack_ref（reports/research_runs/<run_id>/manifest.json）→ runId，供 Report Viewer 連結。 */
export function runIdFromReportRef(ref: string | null | undefined): string | null {
  if (!ref) return null
  const m = ref.match(/research_runs\/([^/]+)\//)
  return m ? m[1] : null
}

/** 觀察進度百分比（observed / observation_days，clamp 0..100）；缺資料回 0。 */
export function observationPct(observed: number | null, total: number | null): number {
  if (!total || total <= 0 || observed == null) return 0
  return Math.min(100, Math.max(0, Math.round((observed / total) * 100)))
}
