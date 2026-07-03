/*
 * OOS 佇列（/live-oos/queue）—— 旅程二入口（rebuild Goal 10）。
 * 所有被人工勾選、待跑 / 正跑昂貴驗證的佇列：策略 / kind / state badge / 勾選 audit（selected_by+reason）/
 * override 標記 / 觀察窗進度（berth）/ 連回 Report Viewer·候選池·策略資產三連。
 * 唯讀決策證據面（消費在後端 after-close tick，ADR-040）；空態引導去候選池勾選。
 * fixture-first：先打 GET /research/live-oos/queue，失敗 fallback 打包契約範例並明示資料來源。
 */
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'
import { useLiveOosQueue } from '../hooks/useLiveOosQueue'
import { QueueCard } from '../components/QueueCard'
import type { LiveOosQueueItem, QueueState } from '../api/queue'

/** chip 顯示順序（在場的 state 才出 chip）。 */
const STATE_ORDER: QueueState[] = ['running', 'queued', 'paused', 'expired', 'completed', 'cancelled']

type StateFilter = 'all' | QueueState

export function LiveOosQueuePage() {
  const { t } = useTranslation('liveOos')
  const errText = useErrorText()
  const navigate = useNavigate()
  const query = useLiveOosQueue()
  const [active, setActive] = useState<StateFilter>('all')

  const source = query.data?.source
  const items = query.data?.items ?? []

  const chips = useMemo(() => {
    const counts = new Map<QueueState, number>()
    for (const it of items) counts.set(it.state, (counts.get(it.state) ?? 0) + 1)
    const stateChips = STATE_ORDER.filter((s) => counts.has(s)).map((s) => ({
      key: s as StateFilter,
      count: counts.get(s) ?? 0,
    }))
    return [{ key: 'all' as StateFilter, count: items.length }, ...stateChips]
  }, [items])

  const visible = useMemo(
    () => (active === 'all' ? items : items.filter((it) => it.state === active)),
    [items, active],
  )

  return (
    <div>
      <PageHeader
        title={t('queue.title')}
        route="/live-oos/queue"
        subtitle={t('queue.subtitle')}
      />

      {/* data source badge —— fixture 模式明示為契約範例示範 */}
      {source === 'fixture' ? (
        <div className="mb-3 flex flex-col gap-1 rounded-lg border border-warning/40 bg-surface px-4 py-2.5">
          <div className="flex items-center gap-2">
            <StatusBadge tone="warning">{t('queue.dataSource.fixture')}</StatusBadge>
          </div>
          <p className="text-xs text-text-muted">{t('queue.dataSource.fixtureHint')}</p>
        </div>
      ) : source === 'api' ? (
        <div className="mb-3">
          <StatusBadge tone="muted">{t('queue.dataSource.live')}</StatusBadge>
        </div>
      ) : null}

      {query.isLoading ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <SkeletonRows rows={4} cols={4} />
        </div>
      ) : query.isError ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">
            {t('errors:load.failed', { resource: t('queue.resource'), detail: errText(query.error) })}
          </p>
          <button
            onClick={() => query.refetch()}
            className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
          >
            {t('common:action.retry')}
          </button>
        </div>
      ) : items.length === 0 ? (
        <FirstRunEmptyState
          headline={t('queue.empty.headline')}
          subtitle={t('queue.empty.subtitle')}
          ctaLabel={t('queue.empty.cta')}
          onCta={() => navigate('/research/candidates')}
        />
      ) : (
        <>
          <QueueFilters chips={chips} active={active} onSelect={setActive} />
          {visible.length === 0 ? (
            <div className="rounded-lg border border-border bg-surface p-6 text-sm text-text-muted">
              {t('queue.filter.noMatch')}
            </div>
          ) : (
            <div className="grid gap-2 lg:grid-cols-2">
              {visible.map((item: LiveOosQueueItem) => (
                <QueueCard key={item.queue_id} item={item} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function QueueFilters({
  chips,
  active,
  onSelect,
}: {
  chips: { key: StateFilter; count: number }[]
  active: StateFilter
  onSelect: (s: StateFilter) => void
}) {
  const { t } = useTranslation('liveOos')
  return (
    <div className="mb-3 flex flex-wrap gap-1.5">
      {chips.map((c) => (
        <button
          key={c.key}
          onClick={() => onSelect(c.key)}
          aria-pressed={active === c.key}
          className={`rounded-md border px-2.5 py-1 text-xs ${
            active === c.key
              ? 'border-text text-text'
              : 'border-border text-text-muted hover:text-text-secondary'
          }`}
        >
          {c.key === 'all' ? t('queue.filter.all') : t(`queue.state.${c.key}`, { defaultValue: c.key })}
          <span className="ml-1 font-mono tabular text-text-muted">{c.count}</span>
        </button>
      ))}
    </div>
  )
}
