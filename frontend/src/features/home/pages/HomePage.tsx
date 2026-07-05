import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ReactNode } from 'react'
import { useRecent, useResearchStatus } from '../hooks/useHome'
import { PendingNote } from '@/components/PendingNote'
import { Skeleton } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { EnumBadge } from '@/components/EnumBadge'
import { StatCard } from '@/components/StatCard'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'

function Panel({
  title,
  eyebrow,
  children,
  action,
}: {
  title: string
  eyebrow?: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section className="border border-border bg-panel">
      <div className="flex min-h-10 items-center justify-between border-b border-border px-3 py-2">
        <div>
          {eyebrow && <div className="text-[10px] uppercase tracking-[0.16em] text-text-muted">{eyebrow}</div>}
          <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-text">{title}</h2>
        </div>
        {action}
      </div>
      <div className="p-3">{children}</div>
    </section>
  )
}

function OpsCell({
  label,
  value,
  tone = 'muted',
}: {
  label: string
  value: string
  tone?: 'gain' | 'warning' | 'error' | 'info' | 'halt' | 'muted'
}) {
  const toneClass: Record<typeof tone, string> = {
    gain: 'text-gain',
    warning: 'text-warning',
    error: 'text-error',
    info: 'text-info',
    halt: 'text-halt',
    muted: 'text-text-secondary',
  }
  return (
    <div className="border border-border bg-row p-3">
      <div className="text-[10px] uppercase tracking-[0.16em] text-text-muted">{label}</div>
      <div className={`mt-1 font-mono text-lg font-semibold tabular ${toneClass[tone]}`}>{value}</div>
    </div>
  )
}

export function HomePage() {
  const navigate = useNavigate()
  const { t } = useTranslation(['home', 'nav', 'common', 'errors'])
  const errText = useErrorText()
  const rs = useResearchStatus()
  const rec = useRecent()
  const status = rs.data?.data
  const recent = rec.data?.data ?? []
  const isNewPlatform = status?.total_runs === 0 && !rs.isLoading

  return (
    <div className="mx-auto flex max-w-[1680px] flex-col gap-3">
      <section className="border border-border-strong bg-panel">
        <div className="grid gap-px bg-border md:grid-cols-[1.35fr_0.65fr]">
          <div className="bg-panel p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-info">Command Center</div>
            <h1 className="mt-1 text-xl font-semibold tracking-tight text-text">Personal EOD Trading Operations</h1>
            <p className="mt-1 max-w-3xl text-sm text-text-secondary">
              Seven-layer control surface for data readiness, research evidence, governance gates, risk locks,
              execution trail, and daily operations. Pending producers stay visible without fabricated values.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => navigate('/research/runs/new')}
                className="border border-info bg-info px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-base"
              >
                New Research Run
              </button>
              <button
                onClick={() => navigate('/deploy/gate')}
                className="border border-border-strong bg-input px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-text-secondary hover:text-text"
              >
                Release Gate
              </button>
              <button
                onClick={() => navigate('/monitor/risk')}
                className="border border-border-strong bg-input px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-text-secondary hover:text-text"
              >
                Risk Blotter
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-px bg-border">
            <OpsCell label="Risk lock" value="CLEAR" tone="gain" />
            <OpsCell label="Mode" value="PAPER" tone="info" />
            <OpsCell label="Data bundle" value="PENDING" tone="warning" />
            <OpsCell label="Broker" value="OFFLINE" tone="muted" />
          </div>
        </div>
      </section>

      {isNewPlatform ? (
        <FirstRunEmptyState headline={t('welcome')} onCta={() => navigate('/research/runs/new')} />
      ) : (
        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="flex flex-col gap-3">
            <Panel title="Research Evidence" eyebrow="Layer 2 · validation">
              {rs.isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : rs.isError ? (
                <div className="border border-error/50 bg-row p-4 text-sm text-error">
                  {t('errors:load.failed', { resource: t('researchStatus'), detail: errText(rs.error) })}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
                  <StatCard label={t('kpi.totalRuns')} value={status?.total_runs ?? '—'} hint="research run ledger" />
                  <StatCard
                    label={t('kpi.latestGate')}
                    value={
                      status?.latest_gate_status ? (
                        <EnumBadge family="gate" value={status.latest_gate_status} />
                      ) : (
                        '—'
                      )
                    }
                    hint="latest truth gate"
                  />
                  <StatCard label={t('kpi.trials')} value={status?.trials ?? t('common:state.awaitingBackend')} />
                  <StatCard label={t('kpi.dsr')} value={status?.dsr ?? t('common:state.awaitingBackend')} />
                </div>
              )}
            </Panel>

            <Panel title="Layer Readiness" eyebrow="Seven-layer operating model">
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {(
                  [
                  ['Data', 'Bundle/DQ pending', 'warning'],
                  ['Research', `${status?.total_runs ?? '—'} runs`, 'info'],
                  ['Governance', status?.latest_gate_status ?? 'awaiting gate', 'muted'],
                  ['Risk', 'fail-closed ready', 'gain'],
                  ['Trading', 'paper mode only', 'info'],
                  ['Execution', 'broker offline', 'muted'],
                  ['Monitoring', 'daily report pending', 'warning'],
                  ['Foundation', 'local runtime', 'muted'],
                ] as Array<[string, string, 'gain' | 'warning' | 'info' | 'muted']>
                ).map(([label, value, tone]) => (
                  <OpsCell key={label} label={label} value={value} tone={tone} />
                ))}
              </div>
            </Panel>
          </div>

          <div className="flex flex-col gap-3">
            <Panel title="Activity Blotter" eyebrow="Recent research + governance events">
              {rec.isLoading ? (
                <Skeleton className="h-28 w-full" />
              ) : recent.length === 0 ? (
                <div className="border border-border bg-row p-4 text-sm text-text-muted">{t('noRecent')}</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[520px] border-collapse text-left text-xs">
                    <thead className="text-[10px] uppercase tracking-[0.14em] text-text-muted">
                      <tr className="border-b border-border">
                        <th className="px-2 py-2 font-medium">Type</th>
                        <th className="px-2 py-2 font-medium">Run ID</th>
                        <th className="px-2 py-2 font-medium">Preset</th>
                        <th className="px-2 py-2 font-medium">Gate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recent.map((r, i) => (
                        <tr
                          key={`${r.run_id ?? 'activity'}-${i}`}
                          onClick={() => r.run_id && navigate(`/research/runs/${encodeURIComponent(r.run_id)}`)}
                          className="cursor-pointer border-b border-border/70 bg-row hover:bg-input"
                        >
                          <td className="px-2 py-2">
                            <StatusBadge tone="muted">{r.type}</StatusBadge>
                          </td>
                          <td className="px-2 py-2 font-mono tabular text-text">{r.run_id}</td>
                          <td className="px-2 py-2 text-text-secondary">{r.preset}</td>
                          <td className="px-2 py-2">
                            {r.gate_status ? <EnumBadge family="gate" value={r.gate_status} /> : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>

            <Panel title="Deferred Producers" eyebrow="Visible gaps, no fabricated values">
              <div className="flex flex-col gap-2">
                <PendingNote label={t('pending.fleet')} />
                <PendingNote label={t('pending.systemHealth')} />
              </div>
            </Panel>
          </div>
        </div>
      )}
    </div>
  )
}
