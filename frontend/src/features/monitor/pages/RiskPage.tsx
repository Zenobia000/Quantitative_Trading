/*
 * Monitor D — 風控指標（monitor_d_risk）。
 * 風控 metrics（/risk/metrics，目前 pending stub → 真實 risk telemetry 接上即點亮）；
 * MDD 趨勢 / 熔斷事件為 pending。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { KpiCard, QueryState } from '../components'
import { useRiskMetrics } from '../hooks/useMonitor'

const RISK_KEYS: { key: string; label: string; pct?: boolean }[] = [
  { key: 'portfolio_heat', label: '組合熱度', pct: true },
  { key: 'max_drawdown', label: 'MaxDD', pct: true },
  { key: 'gross_exposure', label: '總曝險', pct: true },
  { key: 'open_positions', label: '持倉數' },
]

export function RiskPage() {
  const q = useRiskMetrics()
  return (
    <div>
      <PageHeader title="風控指標" route="/monitor/risk" subtitle="ex-ante 風控 + 熔斷狀態" />
      <section className="mb-3">
        <QueryState q={q} pendingLabel="風控 metrics（待 risk telemetry producer）" emptyLabel="尚無風控資料">
          {(m: Record<string, unknown>) => (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {RISK_KEYS.map((c) => (
                <KpiCard key={c.key} label={c.label} value={m[c.key]} pct={c.pct} />
              ))}
            </div>
          )}
        </QueryState>
      </section>
      <PendingNote label="MaxDD 趨勢 / 熔斷事件（risk/mdd-trend · risk/events 端點待 producer）" />
    </div>
  )
}
