/*
 * Enum 顯示映射：raw backend enum → tone（TS，不翻譯）+ i18n key（status namespace）。
 * 集中原本散落各頁的 gateTone/statusTone/STATE_* 表。未知 token → tone 'muted' + label 回退 raw。
 */
export type Tone = 'gain' | 'loss' | 'warning' | 'error' | 'muted'
export type EnumFamily =
  | 'gate'
  | 'validation'
  | 'stage'
  | 'job'
  | 'session'
  | 'criterion'
  | 'watchState'
  | 'timerHealth'

const TONE: Record<EnumFamily, Record<string, Tone>> = {
  gate: { PASS: 'gain', FAIL: 'error', INCOMPLETE: 'warning' },
  validation: {
    draft: 'muted',
    is_pass: 'gain',
    is_fail: 'loss',
    wfa_pass: 'gain',
    wfa_fail: 'loss',
    oos_pass: 'gain',
    oos_fail: 'loss',
  },
  stage: { draft: 'muted', paper: 'warning', live: 'gain' },
  job: { queued: 'muted', running: 'warning', done: 'gain', failed: 'error' },
  session: { OK: 'gain', FAILED: 'error', NO_DATA: 'muted', SKIP: 'muted' },
  criterion: { edge: 'gain', guard: 'muted' },
  // Paper-Watch 觀察艙艙位狀態（active/paused/expired/exited）。
  watchState: { active: 'gain', paused: 'warning', expired: 'muted', exited: 'muted' },
  // after-close.timer 健康度（never_ran=尚未執行 → warning；stale=可能未在跑 → error）。
  timerHealth: { ok: 'gain', stale: 'error', never_ran: 'warning' },
}

export function enumTone(family: EnumFamily, raw?: string | null): Tone {
  if (!raw) return 'muted'
  return TONE[family]?.[raw] ?? 'muted'
}
