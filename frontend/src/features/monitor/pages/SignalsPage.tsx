/*
 * Monitor C — 訊號日誌（monitor_c_signals）。
 * 訊號表 + 成交表（真實 telemetry：/signals · /fills）；漏斗為 pending。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { QueryState, SimpleTable } from '../components'
import type { FillRow, SignalRow } from '../hooks/useMonitor'
import { useFills, useSignals } from '../hooks/useMonitor'

export function SignalsPage() {
  const signals = useSignals()
  const fills = useFills()
  return (
    <div>
      <PageHeader title="訊號日誌" route="/monitor/signals" subtitle="訊號 → 成交（paper/live）" />

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">最近訊號</div>
        <QueryState q={signals} pendingLabel="訊號（待 paper telemetry）" emptyLabel="尚無訊號">
          {(rows: SignalRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'signal_time', label: '時間', fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'stock_id', label: '股票' },
                { key: 'action', label: '動作' },
                { key: 'priority', label: '優先' },
                { key: 'submitted', label: '已送單', fmt: (v) => (v ? '✓' : '—') },
                { key: 'strategy_id', label: '策略' },
              ]}
            />
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">最近成交</div>
        <QueryState q={fills} pendingLabel="成交（待 paper telemetry）" emptyLabel="尚無成交">
          {(rows: FillRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'created_at', label: '時間', fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'stock_id', label: '股票' },
                { key: 'side', label: '方向' },
                { key: 'quantity', label: '股數', fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                { key: 'price', label: '價格' },
                { key: 'status', label: '狀態' },
              ]}
            />
          )}
        </QueryState>
      </section>

      <PendingNote label="訊號漏斗 / 時間軸（signals/funnel · signals/timeline 端點待 producer）" />
    </div>
  )
}
