/*
 * Monitor — 策略艦隊總控（monitor_fleet）。
 * 組合摘要（/portfolio-summary）+ 艦隊板（/fleet：每策略最新淨值，telemetry-driven，
 * 8.H.8）。多策略實跑後自動點亮；單策略時即顯該策略。相關性矩陣已 wired
 * （typed-empty pending），producer 上線即點亮。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { Correlation, FleetRow, PortfolioSummary } from '../hooks/useMonitor'
import { useCorrelation, useFleet, usePortfolioSummary } from '../hooks/useMonitor'

export function FleetPage() {
  const { t } = useTranslation('monitor')
  const summary = usePortfolioSummary()
  const fleet = useFleet()
  const correlation = useCorrelation()
  return (
    <div>
      <PageHeader title={t('fleet.title')} route="/monitor" subtitle={t('fleet.subtitle')} />

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('fleet.summary.heading')}</div>
        <QueryState
          q={summary}
          resource={t('fleet.summary.resource')}
          pendingLabel={t('fleet.summary.pending')}
          emptyLabel={t('fleet.summary.empty')}
        >
          {(s: PortfolioSummary) => (
            <div className="grid grid-cols-3 gap-2">
              <KpiCard label={t('fleet.summary.strategies')} value={s.n_strategies} />
              <KpiCard label={t('fleet.summary.totalEquity')} value={s.total_equity} />
              <KpiCard label={t('fleet.summary.totalPositions')} value={s.total_open_positions} />
            </div>
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('fleet.board.heading')}</div>
        <QueryState
          q={fleet}
          resource={t('fleet.board.resource')}
          pendingLabel={t('fleet.board.pending')}
          emptyLabel={t('fleet.board.empty')}
        >
          {(rows: FleetRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'strategy_id', label: t('fleet.board.col.strategy') },
                { key: 'equity', label: t('fleet.board.col.equity'), fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                { key: 'open_positions', label: t('fleet.board.col.positions') },
                {
                  key: 'portfolio_heat',
                  label: t('fleet.board.col.heat'),
                  fmt: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—'),
                },
                { key: 'last_update', label: t('fleet.board.col.updated'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
              ]}
            />
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('fleet.correlation.heading')}</div>
        <QueryState
          q={correlation}
          resource={t('fleet.correlation.resource')}
          pendingLabel={t('fleet.correlation.pending')}
          emptyLabel={t('fleet.correlation.empty')}
        >
          {(c: Correlation) => (
            <div className="border border-border bg-surface p-3 text-sm text-text-secondary">
              {t('fleet.correlation.summary', { n: c.axes.length })}
              <div className="mt-1 font-mono text-xs text-text-muted">{c.axes.join(' · ')}</div>
            </div>
          )}
        </QueryState>
      </section>
    </div>
  )
}
