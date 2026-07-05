/*
 * Monitor — 運行看板（monitor_board，A2）。
 * runs 表的活狀態看板：run_persist / run-batch 鏡射的生命週期
 * （running → done|failed）+ 審判庭 verdict + 核心 metrics，10s 輪詢。
 * in-flight run 的 verdict/metrics 為 null → 顯示 —，絕不捏造。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { EnumBadge } from '@/components/EnumBadge'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { BoardRow } from '../hooks/useMonitor'
import { useRunsBoard } from '../hooks/useMonitor'

const fmtSharpe = (m: unknown) => {
  const s = (m as Record<string, number> | null)?.sharpe
  return typeof s === 'number' ? s.toFixed(3) : '—'
}
const fmtWindow = (r: BoardRow) =>
  r.is_start && r.is_end ? `${r.is_start} ~ ${r.is_end}` : '—'

export function BoardPage() {
  const { t } = useTranslation('monitor')
  const board = useRunsBoard()
  return (
    <div>
      <PageHeader title={t('board.title')} route="/monitor/board" subtitle={t('board.subtitle')} />

      <QueryState
        q={board}
        resource={t('board.resource')}
        pendingLabel={t('board.pending')}
        emptyLabel={t('board.empty')}
      >
        {(rows: BoardRow[]) => {
          const byStatus = (s: string) => rows.filter((r) => r.status === s)
          return (
            <>
              <section className="mb-3">
                <div className="grid grid-cols-4 gap-2">
                  <KpiCard label={t('board.kpi.total')} value={rows.length} />
                  <KpiCard label={t('board.kpi.running')} value={byStatus('running').length} />
                  <KpiCard label={t('board.kpi.done')} value={byStatus('done').length} />
                  <KpiCard label={t('board.kpi.failed')} value={byStatus('failed').length} />
                </div>
              </section>

              <section className="mb-3">
                <div className="mb-1 text-xs text-text-muted">{t('board.recent')}</div>
                <SimpleTable
                  rows={rows.map((r) => ({ ...r, window: fmtWindow(r) }))}
                  cols={[
                    { key: 'run_id', label: t('board.col.run') },
                    { key: 'strategy', label: t('board.col.strategy') },
                    {
                      key: 'stocks',
                      label: t('board.col.stocks'),
                      fmt: (v) => (Array.isArray(v) ? v.join(', ') : '—'),
                    },
                    { key: 'window', label: t('board.col.window') },
                    { key: 'status', label: t('board.col.status'), fmt: (v) => <EnumBadge family="job" value={v as string} /> },
                    { key: 'gate_status', label: t('board.col.gate'), fmt: (v) => <EnumBadge family="gate" value={v as string | null} /> },
                    { key: 'metrics', label: t('board.col.sharpe'), fmt: fmtSharpe },
                    {
                      key: 'created_at',
                      label: t('board.col.created'),
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
