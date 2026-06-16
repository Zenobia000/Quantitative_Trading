/*
 * Monitor — 策略艦隊總控（monitor_fleet）。
 * 組合摘要（/portfolio-summary）+ 艦隊板（/fleet：每策略最新淨值，telemetry-driven，
 * 8.H.8）。多策略實跑後自動點亮；單策略時即顯該策略。相關性矩陣仍 pending。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { FleetRow, PortfolioSummary } from '../hooks/useMonitor'
import { useFleet, usePortfolioSummary } from '../hooks/useMonitor'

export function FleetPage() {
  const summary = usePortfolioSummary()
  const fleet = useFleet()
  return (
    <div>
      <PageHeader title="策略艦隊總控" route="/monitor" subtitle="多策略配置與健康（ADR-022 fleet）" />

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">組合摘要</div>
        <QueryState q={summary} pendingLabel="組合摘要（待 paper telemetry）" emptyLabel="尚無組合資料">
          {(s: PortfolioSummary) => (
            <div className="grid grid-cols-3 gap-2">
              <KpiCard label="在跑策略" value={s.n_strategies} />
              <KpiCard label="總淨值" value={s.total_equity} />
              <KpiCard label="總持倉" value={s.total_open_positions} />
            </div>
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">艦隊（每策略最新）</div>
        <QueryState q={fleet} pendingLabel="艦隊（待多策略實跑 telemetry）" emptyLabel="尚無在跑策略">
          {(rows: FleetRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'strategy_id', label: '策略' },
                { key: 'equity', label: '淨值', fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                { key: 'open_positions', label: '持倉' },
                {
                  key: 'portfolio_heat',
                  label: '熱度',
                  fmt: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—'),
                },
                { key: 'last_update', label: '更新', fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
              ]}
            />
          )}
        </QueryState>
      </section>

      <PendingNote label="相關性矩陣 / fleet action（correlation 端點待 producer；action 需 live 控制）" />
    </div>
  )
}
