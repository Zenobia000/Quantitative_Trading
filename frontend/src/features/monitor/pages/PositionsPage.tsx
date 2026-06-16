/*
 * Monitor B — 部位狀態（monitor_b_positions）。
 * 未平倉部位表（真實 telemetry：/positions/snapshot）；產業/集中度為 pending。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { QueryState, SimpleTable } from '../components'
import type { PositionRow } from '../hooks/useMonitor'
import { usePositions } from '../hooks/useMonitor'

export function PositionsPage() {
  const q = usePositions()
  return (
    <div>
      <PageHeader title="部位狀態" route="/monitor/positions" subtitle="未平倉部位（paper/live）" />
      <section className="mb-3">
        <QueryState q={q} pendingLabel="部位快照（待 paper telemetry）" emptyLabel="目前無未平倉部位">
          {(rows: PositionRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'stock_id', label: '股票' },
                { key: 'quantity', label: '股數', fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                { key: 'entry_price', label: '進場價' },
                { key: 'stop_loss', label: '停損' },
                { key: 'opened_at', label: '進場時間', fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'strategy_id', label: '策略' },
              ]}
            />
          )}
        </QueryState>
      </section>
      <PendingNote label="產業配置 / 集中度 / 即時報價（industry-allocation · concentration · prices 端點待 producer）" />
    </div>
  )
}
