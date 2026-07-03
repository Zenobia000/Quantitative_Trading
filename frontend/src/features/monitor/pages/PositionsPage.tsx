/*
 * Monitor B — 部位狀態（monitor_b_positions）。
 * 未平倉部位表（真實 telemetry：/positions/snapshot）；產業/集中度為 pending。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { QueryState, SimpleTable } from '../components'
import type { PositionRow } from '../hooks/useMonitor'
import { usePositions } from '../hooks/useMonitor'

export function PositionsPage() {
  const { t } = useTranslation('monitor')
  const q = usePositions()
  return (
    <div>
      <PageHeader title={t('positions.title')} route="/monitor/positions" subtitle={t('positions.subtitle')} />
      <section className="mb-3">
        <QueryState
          q={q}
          resource={t('positions.resource')}
          pendingLabel={t('positions.pending')}
          emptyLabel={t('positions.empty')}
        >
          {(rows: PositionRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'stock_id', label: t('positions.col.stock') },
                { key: 'quantity', label: t('positions.col.shares'), fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                { key: 'entry_price', label: t('positions.col.entryPrice') },
                { key: 'stop_loss', label: t('positions.col.stopLoss') },
                { key: 'opened_at', label: t('positions.col.openedAt'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'strategy_id', label: t('positions.col.strategy') },
              ]}
            />
          )}
        </QueryState>
      </section>
      <PendingNote label={t('positions.deferred')} />
    </div>
  )
}
