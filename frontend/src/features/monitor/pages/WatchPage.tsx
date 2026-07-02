/*
 * Monitor — Paper-Watch 觀察艙（monitor_watch，ADR-033 GUI补）。
 * 補審查缺陷 #17（paper 階段介面覆蓋率趨近零）：排程本體留 systemd，GUI 負責「看見與管理」。
 * 每個艙位：狀態 badge、觀察日 N/~60 進度、到期倒數、DSR、timer 健康度（ok/stale/never_ran）、
 * 最近 session 時間線、暫停/恢復鈕。timer stale/never_ran 附可複製的 systemd 安裝指令。
 */
import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { StatusBadge } from '@/components/StatusBadge'
import { QueryState } from '../components'
import type { TimerHealth, WatchRow, WatchState } from '../hooks/useWatch'
import { useWatchOverview, useWatchToggle } from '../hooks/useWatch'

const TIMER_CMD = 'systemctl --user enable --now after-close.timer'

const STATE_TONE: Record<WatchState, 'gain' | 'warning' | 'muted'> = {
  active: 'gain',
  paused: 'warning',
  expired: 'muted',
  exited: 'muted',
}
const STATE_LABEL: Record<WatchState, string> = {
  active: '觀察中',
  paused: '已暫停',
  expired: '已期滿',
  exited: '已出艙',
}

const SESSION_TONE: Record<string, 'gain' | 'error' | 'warning' | 'muted'> = {
  OK: 'gain',
  FAILED: 'error',
  NO_DATA: 'warning',
  SKIP: 'muted',
}

export function WatchPage() {
  const overview = useWatchOverview()
  return (
    <div>
      <PageHeader
        title="Paper-Watch 觀察艙"
        route="/monitor/watch"
        subtitle="零資金 3 個月觀察窗（ADR-033）· 排程本體 systemd，此處負責看見與管理"
      />
      <QueryState
        q={overview}
        pendingLabel="觀察艙（待 registry）"
        emptyLabel="目前無觀察艙艙位（尚無 PAPER_WATCH 策略進艙）"
      >
        {(rows: WatchRow[]) => (
          <div className="flex flex-col gap-3">
            {rows.map((row) => (
              <WatchCard key={row.strategy} row={row} />
            ))}
          </div>
        )}
      </QueryState>
    </div>
  )
}

function WatchCard({ row }: { row: WatchRow }) {
  const toggle = useWatchToggle()
  const paused = row.status === 'paused'
  const terminal = row.status === 'expired' || row.status === 'exited'
  const pct = row.nominal_trading_days > 0
    ? Math.min(100, Math.round((row.observed_trading_days / row.nominal_trading_days) * 100))
    : 0

  const onToggle = () =>
    toggle.mutate({ strategy: row.strategy, action: paused ? 'resume' : 'pause' })

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      {/* header */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="text-[18px] font-semibold">{row.strategy}</h2>
        <StatusBadge tone={STATE_TONE[row.status]}>{STATE_LABEL[row.status]}</StatusBadge>
        <span className="ml-auto font-mono text-xs text-text-muted tabular">
          DSR {row.verdict_dsr.toFixed(4)}
        </span>
      </div>

      {/* observation progress + expiry */}
      <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <div className="mb-1 flex items-baseline justify-between text-xs text-text-muted">
            <span>觀察日</span>
            <span className="font-mono tabular text-text-secondary">
              {row.observed_trading_days}/~{row.nominal_trading_days}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-raised" role="progressbar" aria-valuenow={pct}>
            <div className="h-full rounded-full bg-gain/70" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="flex flex-col justify-center text-sm">
          <div className="text-xs text-text-muted">到期 {row.expiry_date}</div>
          <div className="font-mono tabular text-text-secondary">
            {row.days_remaining >= 0 ? `剩 ${row.days_remaining} 天` : `已逾期 ${-row.days_remaining} 天`}
          </div>
        </div>
      </div>

      {/* timer health */}
      <TimerHealthBlock health={row.timer_health} lastDate={row.last_session_date} lastTradingDay={row.last_trading_day} />

      {/* recent sessions timeline */}
      <div className="mt-3">
        <div className="mb-1 text-xs text-text-muted">最近 session</div>
        {row.sessions.length === 0 ? (
          <span className="text-sm text-text-muted">尚無 session 紀錄</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {row.sessions.map((s) => (
              <StatusBadge key={s.date} tone={SESSION_TONE[s.status] ?? 'muted'}>
                <span className="font-mono tabular">{s.date.slice(5)}</span>
                <span>{s.status}</span>
              </StatusBadge>
            ))}
          </div>
        )}
      </div>

      {/* pause / resume */}
      <div className="mt-3 flex items-center gap-2 border-t border-border/50 pt-3">
        <button
          onClick={onToggle}
          disabled={toggle.isPending || terminal}
          title={terminal ? '已終止的艙位無法暫停/恢復' : undefined}
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:text-text disabled:opacity-50"
        >
          {toggle.isPending ? '處理中…' : paused ? '恢復觀察 ▶' : '暫停觀察 ⏸'}
        </button>
        {paused && <span className="text-xs text-warning">已暫停 · after-close 每日略過此艙（不發告警）</span>}
        {toggle.isError && <span className="text-xs text-error">{(toggle.error as Error)?.message}</span>}
      </div>
    </section>
  )
}

function TimerHealthBlock({
  health,
  lastDate,
  lastTradingDay,
}: {
  health: TimerHealth
  lastDate: string | null
  lastTradingDay: string
}) {
  if (health === 'ok') {
    return (
      <div className="flex items-center gap-2 rounded-md border border-gain/40 bg-surface px-3 py-2 text-sm">
        <StatusBadge tone="gain">排程正常</StatusBadge>
        <span className="text-text-secondary">最後成功 session {lastDate}</span>
      </div>
    )
  }
  const isNever = health === 'never_ran'
  return (
    <div className="rounded-md border border-error/40 bg-surface px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <StatusBadge tone={isNever ? 'warning' : 'error'}>
          {isNever ? '尚未執行' : '排程可能未在跑'}
        </StatusBadge>
        <span className="text-text-secondary">
          {isNever
            ? '此艙位尚無任何 after-close session 紀錄'
            : `最後成功 session ${lastDate ?? '—'}，但上一交易日 ${lastTradingDay} 應已產生 marker`}
        </span>
      </div>
      <p className="mt-2 text-xs text-text-muted">
        {isNever ? '若已進艙，請在部署主機啟用排程器：' : '請在部署主機確認 systemd timer 已啟用：'}
      </p>
      <CommandBlock cmd={TIMER_CMD} />
      <p className="mt-1 text-xs text-text-muted">
        詳見 <span className="font-mono">deploy/README</span> 的 after-close.timer 安裝段。
      </p>
    </div>
  )
}

function CommandBlock({ cmd }: { cmd: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    void navigator.clipboard?.writeText(cmd)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="mt-1 flex items-center gap-2 rounded-md border border-border bg-surface-raised px-2 py-1">
      <code className="flex-1 overflow-x-auto font-mono text-xs text-text-secondary">{cmd}</code>
      <button
        onClick={copy}
        className="shrink-0 rounded border border-border px-2 py-0.5 text-xs text-text-muted hover:text-text"
      >
        {copied ? '已複製' : '複製'}
      </button>
    </div>
  )
}
