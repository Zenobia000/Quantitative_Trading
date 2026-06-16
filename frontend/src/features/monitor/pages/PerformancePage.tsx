/*
 * Monitor A — 績效總覽（monitor_a_performance）。
 * KPI tiles + equity 曲線（真實 telemetry：/performance/kpi · /equity）；
 * benchmark / monthly 端點為 pending stub → PendingNote（不假造）。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { EquityPoint, PerfKpi } from '../hooks/useMonitor'
import { usePerfEquity, usePerfKpi } from '../hooks/useMonitor'

const KPIS: { key: keyof PerfKpi; label: string; pct?: boolean; signed?: boolean }[] = [
  { key: 'current_equity', label: '淨值' },
  { key: 'total_return', label: '總報酬', pct: true, signed: true },
  { key: 'cagr', label: 'CAGR', pct: true, signed: true },
  { key: 'sharpe', label: 'Sharpe' },
  { key: 'max_drawdown', label: 'MaxDD', pct: true },
  { key: 'calmar', label: 'Calmar' },
]

export function PerformancePage() {
  const kpi = usePerfKpi()
  const equity = usePerfEquity()
  return (
    <div>
      <PageHeader title="績效總覽" route="/monitor/performance" subtitle="paper/live telemetry（daemon 餵入即點亮）" />

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">KPI</div>
        <QueryState q={kpi} pendingLabel="績效 KPI（待 paper telemetry）" emptyLabel="尚無 KPI">
          {(k: PerfKpi) => (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
              {KPIS.map((c) => (
                <KpiCard key={c.key} label={c.label} value={k[c.key]} pct={c.pct} signed={c.signed} />
              ))}
            </div>
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">Equity 曲線（最近）</div>
        <QueryState q={equity} pendingLabel="equity 序列（待 paper telemetry）" emptyLabel="尚無 equity 點">
          {(pts: EquityPoint[]) => (
            <SimpleTable
              rows={pts.slice(-30)}
              cols={[
                { key: 't', label: '時間', fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'equity', label: '淨值', fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                {
                  key: 'drawdown',
                  label: 'DD',
                  fmt: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '—'),
                },
              ]}
            />
          )}
        </QueryState>
      </section>

      <PendingNote label="基準對比 / 月報酬熱圖（benchmark · monthly 端點待 producer）" />
    </div>
  )
}
