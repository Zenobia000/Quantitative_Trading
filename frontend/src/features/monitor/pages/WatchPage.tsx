/*
 * Monitor — Paper-Watch 觀察艙（monitor_watch，ADR-033 GUI补）。
 * 補審查缺陷 #17（paper 階段介面覆蓋率趨近零）：排程本體留 systemd，GUI 負責「看見與管理」。
 * 每個艙位：狀態 badge、觀察日 N/~60 進度、到期倒數、DSR、timer 健康度（ok/stale/never_ran）、
 * 最近 session 時間線、暫停/恢復鈕。timer stale/never_ran 附可複製的 systemd 安裝指令。
 */
import { useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { StatusBadge } from '@/components/StatusBadge'
import { EnumBadge } from '@/components/EnumBadge'
import { useEnumLabel } from '@/i18n/useEnumLabel'
import { useErrorText } from '@/i18n/useErrorText'
import { QueryState } from '../components'
import type { TimerHealth, WatchRow, WatchSession } from '../hooks/useWatch'
import { useWatchOverview, useWatchToggle } from '../hooks/useWatch'

const TIMER_CMD = 'systemctl --user enable --now after-close.timer'

export function WatchPage() {
  const { t } = useTranslation('monitor')
  const overview = useWatchOverview()
  return (
    <div>
      <PageHeader title={t('watch.title')} route="/monitor/watch" subtitle={t('watch.subtitle')} />
      <QueryState
        q={overview}
        resource={t('watch.resource')}
        pendingLabel={t('watch.pending')}
        emptyLabel={t('watch.empty')}
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
  const { t } = useTranslation('monitor')
  const errText = useErrorText()
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
        <EnumBadge family="watchState" value={row.status} />
        <span className="ml-auto font-mono text-xs text-text-muted tabular">
          DSR {row.verdict_dsr.toFixed(4)}
        </span>
      </div>

      {/* observation progress + expiry */}
      <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <div className="mb-1 flex items-baseline justify-between text-xs text-text-muted">
            <span>{t('watch.observedDays')}</span>
            <span className="font-mono tabular text-text-secondary">
              {row.observed_trading_days}/~{row.nominal_trading_days}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-raised" role="progressbar" aria-valuenow={pct}>
            <div className="h-full rounded-full bg-gain/70" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="flex flex-col justify-center text-sm">
          <div className="text-xs text-text-muted">{t('watch.expiry', { date: row.expiry_date })}</div>
          <div className="font-mono tabular text-text-secondary">
            {row.days_remaining >= 0
              ? t('watch.daysRemaining', { days: row.days_remaining })
              : t('watch.overdue', { days: -row.days_remaining })}
          </div>
        </div>
      </div>

      {/* timer health */}
      <TimerHealthBlock health={row.timer_health} lastDate={row.last_session_date} lastTradingDay={row.last_trading_day} />

      {/* recent sessions timeline */}
      <div className="mt-3">
        <div className="mb-1 text-xs text-text-muted">{t('watch.recentSessions')}</div>
        {row.sessions.length === 0 ? (
          <span className="text-sm text-text-muted">{t('watch.noSessions')}</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {row.sessions.map((s) => (
              <SessionBadge key={s.date} session={s} />
            ))}
          </div>
        )}
      </div>

      {/* pause / resume */}
      <div className="mt-3 flex items-center gap-2 border-t border-border/50 pt-3">
        <button
          onClick={onToggle}
          disabled={toggle.isPending || terminal}
          title={terminal ? t('watch.terminalHint') : undefined}
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:text-text disabled:opacity-50"
        >
          {toggle.isPending ? t('watch.processing') : paused ? t('watch.resume') : t('watch.pause')}
        </button>
        {paused && <span className="text-xs text-warning">{t('watch.pausedNote')}</span>}
        {toggle.isError && <span className="text-xs text-error">{errText(toggle.error)}</span>}
      </div>
    </section>
  )
}

/** 單一 session 徽章：日期（mono）+ 本地化狀態（OK→成功…），tone 由 displayMap 決定。 */
function SessionBadge({ session }: { session: WatchSession }) {
  const { label, tone } = useEnumLabel('session', session.status)
  return (
    <StatusBadge tone={tone}>
      <span className="font-mono tabular">{session.date.slice(5)}</span>
      <span>{label}</span>
    </StatusBadge>
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
  const { t } = useTranslation('monitor')
  if (health === 'ok') {
    return (
      <div className="flex items-center gap-2 rounded-md border border-gain/40 bg-surface px-3 py-2 text-sm">
        <EnumBadge family="timerHealth" value="ok" />
        <span className="text-text-secondary">{t('watch.timer.okDetail', { date: lastDate })}</span>
      </div>
    )
  }
  const isNever = health === 'never_ran'
  return (
    <div className="rounded-md border border-error/40 bg-surface px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <EnumBadge family="timerHealth" value={health} />
        <span className="text-text-secondary">
          {isNever
            ? t('watch.timer.neverDetail')
            : t('watch.timer.staleDetail', { date: lastDate ?? '—', day: lastTradingDay })}
        </span>
      </div>
      <p className="mt-2 text-xs text-text-muted">
        {isNever ? t('watch.timer.neverHint') : t('watch.timer.staleHint')}
      </p>
      <CommandBlock cmd={TIMER_CMD} />
      <p className="mt-1 text-xs text-text-muted">
        <Trans
          t={t}
          i18nKey="watch.timer.docsHint"
          values={{ path: 'deploy/README' }}
          components={[<span className="font-mono" />]}
        />
      </p>
    </div>
  )
}

function CommandBlock({ cmd }: { cmd: string }) {
  const { t } = useTranslation('common')
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
        {copied ? t('action.copied') : t('action.copy')}
      </button>
    </div>
  )
}
