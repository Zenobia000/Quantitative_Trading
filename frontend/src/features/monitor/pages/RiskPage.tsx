/*
 * Monitor D — 風控指標（monitor_d_risk）。
 * 風控 metrics（/risk/metrics，目前 pending stub → 真實 risk telemetry 接上即點亮）；
 * MDD 趨勢 / 熔斷事件為 pending。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { KpiCard, QueryState } from '../components'
import { useRiskMetrics } from '../hooks/useMonitor'

const RISK_KEYS: { key: string; labelKey: string; pct?: boolean }[] = [
  { key: 'portfolio_heat', labelKey: 'risk.portfolioHeat', pct: true },
  { key: 'max_drawdown', labelKey: 'risk.maxDrawdown', pct: true },
  { key: 'gross_exposure', labelKey: 'risk.grossExposure', pct: true },
  { key: 'open_positions', labelKey: 'risk.openPositions' },
]

export function RiskPage() {
  const { t } = useTranslation('monitor')
  const q = useRiskMetrics()
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
      <PendingNote label={t('risk.deferred')} />
    </div>
  )
}
