/*
 * Monitor C — 訊號日誌（monitor_c_signals）。
 * 訊號表 + 成交表（真實 telemetry：/signals · /fills）；漏斗為 pending。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { QueryState, SimpleTable } from '../components'
import type { FillRow, SignalRow } from '../hooks/useMonitor'
import { useFills, useSignals } from '../hooks/useMonitor'

export function SignalsPage() {
  const { t } = useTranslation('monitor')
  const signals = useSignals()
  const fills = useFills()
  return (
    <div>
      <PageHeader title={t('signals.title')} route="/monitor/signals" subtitle={t('signals.subtitle')} />

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('signals.signalsHeading')}</div>
        <QueryState
          q={signals}
          resource={t('signals.signalsResource')}
          pendingLabel={t('signals.signalsPending')}
          emptyLabel={t('signals.signalsEmpty')}
        >
          {(rows: SignalRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'signal_time', label: t('signals.signalCol.time'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'stock_id', label: t('signals.signalCol.stock') },
                { key: 'action', label: t('signals.signalCol.action') },
                { key: 'priority', label: t('signals.signalCol.priority') },
                { key: 'submitted', label: t('signals.signalCol.submitted'), fmt: (v) => (v ? '✓' : '—') },
                { key: 'strategy_id', label: t('signals.signalCol.strategy') },
              ]}
            />
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('signals.fillsHeading')}</div>
        <QueryState
          q={fills}
          resource={t('signals.fillsResource')}
          pendingLabel={t('signals.fillsPending')}
          emptyLabel={t('signals.fillsEmpty')}
        >
          {(rows: FillRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'created_at', label: t('signals.fillCol.time'), fmt: (v) => String(v).replace('T', ' ').slice(0, 19) },
                { key: 'stock_id', label: t('signals.fillCol.stock') },
                { key: 'side', label: t('signals.fillCol.side') },
                { key: 'quantity', label: t('signals.fillCol.shares'), fmt: (v) => (typeof v === 'number' ? v.toLocaleString() : '—') },
                { key: 'price', label: t('signals.fillCol.price') },
                { key: 'status', label: t('signals.fillCol.status') },
              ]}
            />
          )}
        </QueryState>
      </section>

      <PendingNote label={t('signals.deferred')} />
    </div>
  )
}
