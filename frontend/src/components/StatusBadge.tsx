/*
 * StatusBadge — 色 + 文字雙編碼（GOAL.md 硬約束 #6）。
 * 唯一彩色僅功能態；一律附文字，不只靠顏色。
 */
type Tone = 'gain' | 'loss' | 'warning' | 'error' | 'muted'

const TONE: Record<Tone, string> = {
  gain: 'text-gain border-gain/40',
  loss: 'text-loss border-loss/40',
  warning: 'text-warning border-warning/40',
  error: 'text-error border-error/40',
  muted: 'text-text-muted border-border',
}

export function StatusBadge({ tone = 'muted', children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs ${TONE[tone]}`}
    >
      {children}
    </span>
  )
}
