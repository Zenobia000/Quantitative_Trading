/*
 * Monitor B — 部位狀態（monitor_b_positions）。
 * 未平倉部位表（真實 telemetry：/positions/snapshot）；產業配置 / 集中度 / 即時報價
 * 已 wired（typed-empty pending），producer 上線即點亮。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { KpiCard, QueryState, SimpleTable } from '../components'
import type { Concentration, IndustryAllocation, PositionRow, PriceQuote } from '../hooks/useMonitor'
import { usePosConcentration, usePosIndustry, usePosPrices, usePositions } from '../hooks/useMonitor'

export function PositionsPage() {
  const { t } = useTranslation('monitor')
  const q = usePositions()
  const industry = usePosIndustry()
  const concentration = usePosConcentration()
  const prices = usePosPrices()
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

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('positions.industryHeading')}</div>
        <QueryState
          q={industry}
          resource={t('positions.industryResource')}
          pendingLabel={t('positions.industryPending')}
          emptyLabel={t('positions.industryEmpty')}
        >
          {(rows: IndustryAllocation[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'industry', label: t('positions.industryCol.industry') },
                {
                  key: 'weight',
                  label: t('positions.industryCol.weight'),
                  align: 'right',
                  fmt: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—'),
                },
              ]}
            />
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('positions.concentrationHeading')}</div>
        <QueryState
          q={concentration}
          resource={t('positions.concentrationResource')}
          pendingLabel={t('positions.concentrationPending')}
          emptyLabel={t('positions.concentrationEmpty')}
        >
          {(c: Concentration) => (
            <div className="grid grid-cols-3 gap-2">
              <KpiCard label={t('positions.concentration.hhi')} value={c.hhi} />
              <KpiCard label={t('positions.concentration.top5')} value={c.top5_weight} pct />
              <KpiCard label={t('positions.concentration.holdings')} value={c.n_holdings} />
            </div>
          )}
        </QueryState>
      </section>

      <section className="mb-3">
        <div className="mb-1 text-xs text-text-muted">{t('positions.pricesHeading')}</div>
        <QueryState
          q={prices}
          resource={t('positions.pricesResource')}
          pendingLabel={t('positions.pricesPending')}
          emptyLabel={t('positions.pricesEmpty')}
        >
          {(rows: PriceQuote[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'stock_id', label: t('positions.priceCol.stock') },
                { key: 'price', label: t('positions.priceCol.price'), align: 'right' },
                { key: 'as_of', label: t('positions.priceCol.asOf'), fmt: (v) => (v ? String(v).replace('T', ' ').slice(0, 19) : '—') },
              ]}
            />
          )}
        </QueryState>
      </section>
    </div>
  )
}
