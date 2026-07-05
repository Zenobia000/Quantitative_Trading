import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ReactNode } from 'react'
import { useHomeFleet, useRecent, useResearchStatus, useSystemHealth } from '../hooks/useHome'
import { PendingNote } from '@/components/PendingNote'
import { isPending } from '@/types/domain'
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
  const sh = useSystemHealth()
  const fleet = useHomeFleet()
  const status = rs.data?.data
  const recent = rec.data?.data ?? []
  const health = sh.data?.data
  const isNewPlatform = status?.total_runs === 0 && !rs.isLoading
  // system-health producer 未落地（M4）→ 狀態帶顯示誠實空態，不假造 CLEAR/PAPER/OFFLINE。
  const awaiting = t('common:state.awaitingBackend')
  const hv = (v?: string) => v ?? '—'

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
            <OpsCell
              label="Risk lock"
              value={hv(health?.risk_lock)}
              tone={health?.risk_lock === 'CLEAR' ? 'gain' : health?.risk_lock ? 'halt' : 'muted'}
            />
            <OpsCell label="Mode" value={hv(health?.mode)} tone={health?.mode ? 'info' : 'muted'} />
            <OpsCell
              label="Data bundle"
              value={hv(health?.data_bundle)}
              tone={health?.data_bundle === 'READY' ? 'gain' : health?.data_bundle ? 'warning' : 'muted'}
            />
            <OpsCell
              label="Broker"
              value={hv(health?.broker)}
              tone={health?.broker === 'ONLINE' ? 'gain' : 'muted'}
            />
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
                  // Data/Research/Governance/Risk/Trading/Execution 由真實 ledger + system-health
                  // 驅動；欄位未落地（M4）顯示誠實 awaiting，不假造 ready/offline 等狀態。
                  ['Data', health?.data_bundle ?? awaiting, health?.data_bundle === 'READY' ? 'gain' : health?.data_bundle ? 'warning' : 'muted'],
                  ['Research', `${status?.total_runs ?? '—'} runs`, 'info'],
                  ['Governance', status?.latest_gate_status ?? 'awaiting gate', 'muted'],
                  ['Risk', health?.risk_lock ?? awaiting, health?.risk_lock === 'CLEAR' ? 'gain' : health?.risk_lock ? 'warning' : 'muted'],
                  ['Trading', health?.mode ?? awaiting, health?.mode ? 'info' : 'muted'],
                  ['Execution', health?.broker ?? awaiting, health?.broker === 'ONLINE' ? 'gain' : 'muted'],
                  ['Monitoring', awaiting, 'muted'],
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

            <Panel title="Strategy Fleet" eyebrow="Paper/live health · today's performance">
              {fleet.isLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : isPending(fleet.data?.meta) || (fleet.data?.data ?? []).length === 0 ? (
                <PendingNote label={t('pending.fleet')} />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[420px] border-collapse text-left text-xs">
                    <thead className="text-[10px] uppercase tracking-[0.14em] text-text-muted">
                      <tr className="border-b border-border">
                        <th className="px-2 py-2 font-medium">Strategy</th>
                        <th className="px-2 py-2 font-medium">Equity</th>
                        <th className="px-2 py-2 font-medium">Open</th>
                        <th className="px-2 py-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(fleet.data?.data ?? []).map((f) => (
                        <tr key={f.strategy_id} className="border-b border-border/70 bg-row">
                          <td className="px-2 py-2 font-mono tabular text-text">{f.strategy_id}</td>
                          <td className="px-2 py-2 font-mono tabular text-text-secondary">{f.equity ?? '—'}</td>
                          <td className="px-2 py-2 font-mono tabular text-text-secondary">{f.open_positions ?? '—'}</td>
                          <td className="px-2 py-2">
                            <StatusBadge tone="muted">{f.status ?? '—'}</StatusBadge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>
          </div>
        </div>
      )}
    </div>
  )
}
