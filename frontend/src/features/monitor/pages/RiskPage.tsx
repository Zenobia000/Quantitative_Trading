/*
 * Monitor D — 風控指標（monitor_d_risk）。
 * 風控 metrics（/risk/metrics，目前 pending stub → 真實 risk telemetry 接上即點亮）；
 * MaxDD 趨勢 / 熔斷事件已 wired（typed-empty pending），producer 上線即點亮。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { MddPoint, RiskEvent } from '../hooks/useMonitor'
import { useRiskEvents, useRiskMddTrend, useRiskMetrics } from '../hooks/useMonitor'

const RISK_KEYS: { key: string; labelKey: string; pct?: boolean }[] = [
  { key: 'portfolio_heat', labelKey: 'risk.portfolioHeat', pct: true },
  { key: 'max_drawdown', labelKey: 'risk.maxDrawdown', pct: true },
  { key: 'gross_exposure', labelKey: 'risk.grossExposure', pct: true },
  { key: 'open_positions', labelKey: 'risk.openPositions' },
]

export function RiskPage() {
  const { t } = useTranslation('monitor')
  const q = useRiskMetrics()
  const mdd = useRiskMddTrend()
  const events = useRiskEvents()
  return (
    <div>
      <PageHeader title={t('risk.title')} route="/monitor/risk" subtitle={t('risk.subtitle')} />
      <section className="mb-3">
        <QueryState
          q={q}
          resource={t('risk.resource')}
          pendingLabel={t('risk.pending')}
          emptyLabel={t('risk.empty')}
        >
          {(m: Record<string, unknown>) => (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {RISK_KEYS.map((c) => (
                <KpiCard key={c.key} label={t(c.labelKey)} value={m[c.key]} pct={c.pct} />
              ))}
            </div>
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('risk.mddHeading')}</div>
        <QueryState
          q={mdd}
          resource={t('risk.mddResource')}
          pendingLabel={t('risk.mddPending')}
          emptyLabel={t('risk.mddEmpty')}
        >
          {(rows: MddPoint[]) => (
            <SimpleTable
              rows={rows.slice(-30)}
              cols={[
                { key: 't', label: t('risk.mddCol.time'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                {
                  key: 'drawdown',
                  label: t('risk.mddCol.drawdown'),
                  align: 'right',
                  fmt: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '—'),
                },
              ]}
            />
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('risk.eventsHeading')}</div>
        <QueryState
          q={events}
          resource={t('risk.eventsResource')}
          pendingLabel={t('risk.eventsPending')}
          emptyLabel={t('risk.eventsEmpty')}
        >
          {(rows: RiskEvent[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'event_time', label: t('risk.eventCol.time'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'kind', label: t('risk.eventCol.kind') },
                { key: 'severity', label: t('risk.eventCol.severity') },
                { key: 'detail', label: t('risk.eventCol.detail') },
              ]}
            />
          )}
        </QueryState>
      </section>
    </div>
  )
}
