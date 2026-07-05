/*
 * Monitor A — 績效總覽（monitor_a_performance）。
 * KPI tiles + equity 曲線（真實 telemetry：/performance/kpi · /equity）；
 * benchmark / monthly 端點已 wired（typed-empty pending），producer 上線即點亮。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { BenchmarkPoint, EquityPoint, MonthlyReturn, PerfKpi } from '../hooks/useMonitor'
import { usePerfBenchmark, usePerfEquity, usePerfKpi, usePerfMonthly } from '../hooks/useMonitor'

const KPIS: { key: keyof PerfKpi; labelKey: string; pct?: boolean; signed?: boolean }[] = [
  { key: 'current_equity', labelKey: 'performance.kpi.currentEquity' },
  { key: 'total_return', labelKey: 'performance.kpi.totalReturn', pct: true, signed: true },
  { key: 'cagr', labelKey: 'performance.kpi.cagr', pct: true, signed: true },
  { key: 'sharpe', labelKey: 'performance.kpi.sharpe' },
  { key: 'max_drawdown', labelKey: 'performance.kpi.maxDrawdown', pct: true },
  { key: 'calmar', labelKey: 'performance.kpi.calmar' },
]

export function PerformancePage() {
  const { t } = useTranslation('monitor')
  const kpi = usePerfKpi()
  const equity = usePerfEquity()
  const benchmark = usePerfBenchmark()
  const monthly = usePerfMonthly()
  return (
    <div>
      <PageHeader title={t('performance.title')} route="/monitor/performance" subtitle={t('performance.subtitle')} />

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('performance.kpiHeading')}</div>
        <QueryState
          q={kpi}
          resource={t('performance.kpiResource')}
          pendingLabel={t('performance.kpiPending')}
          emptyLabel={t('performance.kpiEmpty')}
        >
          {(k: PerfKpi) => (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
              {KPIS.map((c) => (
                <KpiCard key={c.key} label={t(c.labelKey)} value={k[c.key]} pct={c.pct} signed={c.signed} />
              ))}
            </div>
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('performance.equityHeading')}</div>
        <QueryState
          q={equity}
          resource={t('performance.equityResource')}
          pendingLabel={t('performance.equityPending')}
          emptyLabel={t('performance.equityEmpty')}
        >
          {(pts: EquityPoint[]) => (
            <SimpleTable
              rows={pts.slice(-30)}
              cols={[
                { key: 't', label: t('performance.col.time'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'equity', label: t('performance.col.equity'), fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                {
                  key: 'drawdown',
                  label: t('performance.col.drawdown'),
                  fmt: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '—'),
                },
              ]}
            />
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('performance.benchmarkHeading')}</div>
        <QueryState
          q={benchmark}
          resource={t('performance.benchmarkResource')}
          pendingLabel={t('performance.benchmarkPending')}
          emptyLabel={t('performance.benchmarkEmpty')}
        >
          {(rows: BenchmarkPoint[]) => (
            <SimpleTable
              rows={rows.slice(-30)}
              cols={[
                { key: 't', label: t('performance.benchmarkCol.time'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'strategy', label: t('performance.benchmarkCol.strategy'), align: 'right' },
                { key: 'benchmark', label: t('performance.benchmarkCol.benchmark'), align: 'right' },
              ]}
            />
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('performance.monthlyHeading')}</div>
        <QueryState
          q={monthly}
          resource={t('performance.monthlyResource')}
          pendingLabel={t('performance.monthlyPending')}
          emptyLabel={t('performance.monthlyEmpty')}
        >
          {(rows: MonthlyReturn[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'month', label: t('performance.monthlyCol.month') },
                {
                  key: 'return_pct',
                  label: t('performance.monthlyCol.return'),
                  align: 'right',
                  fmt: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '—'),
                },
              ]}
            />
          )}
        </QueryState>
      </section>
    </div>
  )
}
