/*
 * Monitor — 運行看板（monitor_board，A2）。
 * runs 表的活狀態看板：run_persist / run-batch 鏡射的生命週期
 * （running → done|failed）+ 審判庭 verdict + 核心 metrics，10s 輪詢。
 * in-flight run 的 verdict/metrics 為 null → 顯示 —，絕不捏造。
 */
import { PageHeader } from '@/components/PageHeader'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { BoardRow } from '../hooks/useMonitor'
import { useRunsBoard } from '../hooks/useMonitor'

const fmtDash = (v: unknown) => (v == null || v === '' ? '—' : String(v))
const fmtSharpe = (m: unknown) => {
  const s = (m as Record<string, number> | null)?.sharpe
  return typeof s === 'number' ? s.toFixed(3) : '—'
}
const fmtWindow = (r: BoardRow) =>
  r.is_start && r.is_end ? `${r.is_start} ~ ${r.is_end}` : '—'

export function BoardPage() {
  const board = useRunsBoard()
  return (
    <div>
      <PageHeader
        title="運行看板"
        route="/monitor/board"
        subtitle="研究 run 生命週期 + 審判庭判決（runs 表，10s 輪詢）"
      />

      <QueryState
        q={board}
        pendingLabel="運行看板（待 TimescaleDB runs 表——跑一次 run-is / run-batch 即點亮）"
        emptyLabel="尚無 run 記錄"
      >
        {(rows: BoardRow[]) => {
          const byStatus = (s: string) => rows.filter((r) => r.status === s)
          return (
            <>
              <section className="mb-3">
                <div className="grid grid-cols-4 gap-2">
                  <KpiCard label="總 runs" value={rows.length} />
                  <KpiCard label="進行中" value={byStatus('running').length} />
                  <KpiCard label="完成" value={byStatus('done').length} />
                  <KpiCard label="失敗" value={byStatus('failed').length} />
                </div>
              </section>

              <section className="mb-3">
                <div className="mb-1 text-xs text-text-muted">
                  最新 runs（新到舊）
                </div>
                <SimpleTable
                  rows={rows.map((r) => ({ ...r, window: fmtWindow(r) }))}
                  cols={[
                    { key: 'run_id', label: 'Run' },
                    { key: 'strategy', label: '策略' },
                    {
                      key: 'stocks',
                      label: '標的',
                      fmt: (v) => (Array.isArray(v) ? v.join(', ') : '—'),
                    },
                    { key: 'window', label: '窗口' },
                    { key: 'status', label: '狀態', fmt: fmtDash },
                    { key: 'gate_status', label: '審判庭', fmt: fmtDash },
                    { key: 'metrics', label: 'Sharpe', fmt: fmtSharpe },
                    {
                      key: 'created_at',
                      label: '建立',
                      fmt: (v) => (v ? String(v).replace('T', ' ').slice(0, 19) : '—'),
                    },
                  ]}
                />
              </section>
            </>
          )
        }}
      </QueryState>
    </div>
  )
}
