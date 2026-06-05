/*
 * 單一 WebSocket：/ws/positions/live（doc 25 §5，M5 才啟用）。
 * Phase 0 僅留接口；realtime 一律 polling，唯此一條 WS。
 */
export type PositionsLiveHandler = (msg: unknown) => void

/** M5 啟用：連 /ws/positions/live。目前為佔位接口。 */
export function connectPositionsLive(_onMessage: PositionsLiveHandler): () => void {
  // TODO(M5): 實作 WebSocket 連線 + 重連 + 心跳。
  // 目前回傳 noop 取消函式。
  return () => {}
}
