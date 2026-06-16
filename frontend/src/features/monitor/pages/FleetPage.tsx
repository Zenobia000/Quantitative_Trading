/*
 * Monitor — 策略艦隊總控（monitor_fleet）。
 * 艦隊策略卡 + 組合摘要（/fleet · /strategies · /portfolio-summary）。多為 pending
 * stub（需 ADR-022 多策略實跑），真實在跑後自動點亮。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { QueryState, SimpleTable } from '../components'
import { useFleet } from '../hooks/useMonitor'

export function FleetPage() {
  const fleet = useFleet()
  return (
    <div>
      <PageHeader title="策略艦隊總控" route="/monitor" subtitle="多策略配置與健康（ADR-022 fleet）" />
      <section className="mb-3">
        <QueryState q={fleet} pendingLabel="艦隊（待多策略實跑 telemetry）" emptyLabel="尚無在跑策略">
          {(rows: unknown[]) => (
            <SimpleTable
              rows={rows as Record<string, unknown>[]}
              cols={[
                { key: 'strategy_id', label: '策略' },
                { key: 'status', label: '狀態' },
                { key: 'weight', label: '配置' },
                { key: 'sharpe', label: 'Sharpe' },
                { key: 'equity', label: '淨值' },
              ]}
            />
          )}
        </QueryState>
      </section>
      <PendingNote label="組合摘要 / 相關性矩陣 / fleet action（portfolio-summary · correlation 端點待 producer）" />
    </div>
  )
}
