/*
 * DatasetCatalog — 資料字典 blotter（authoring-first）。
 *
 * 定位：這是「策略作者的資料字典」——
 * 搜有什麼資料可以寫策略、複製 key、看本地有無 + 我的策略庫誰在用。**不是**快取運維
 * 儀表板，故不呈現 staleness / coverage / manifest。
 *
 * 狀態唯二：本地已有(cached)/未下載(not_cached) 的二元、與策略庫反向索引(used_by)。
 * 分類 chip + 搜尋（比對 key + name_zh + description）全在前端做，資料一次拉全量。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { CopyButton } from '@/components/CopyButton'
import { QueryState } from '@/features/monitor/components'
import { useDatasets } from '../hooks/useSystem'
import type { DatasetCard } from '../hooks/useSystem'

/** 分類 chip 排序（對齊 finlab_catalog 的 slug；顯示名走 i18n）。 */
const CATEGORY_ORDER = [
  'price_volume',
  'institutional',
  'financials',
  'monthly_revenue',
  'margin_short',
] as const

/** freq raw（日/月/季）→ i18n 子 key，未知則回退原字串。 */
const FREQ_KEY: Record<string, string> = { '日': 'daily', '月': 'monthly', '季': 'quarterly' }

const inputCls =
  'w-full border border-border bg-base px-3 py-1.5 text-sm text-text placeholder:text-text-muted'

/** 前端過濾：分類精確、搜尋在 key + name_zh + description 上做不分大小寫子字串。 */
function filterCards(cards: DatasetCard[], category: string | null, search: string): DatasetCard[] {
  const needle = search.trim().toLowerCase()
  return cards.filter((c) => {
    if (category && c.category !== category) return false
    if (!needle) return true
    return (
      c.key.toLowerCase().includes(needle) ||
      c.name_zh.toLowerCase().includes(needle) ||
      c.description.toLowerCase().includes(needle)
    )
  })
}

function CategoryChips({
  active,
  onChange,
}: {
  active: string | null
  onChange: (c: string | null) => void
}) {
  const { t } = useTranslation('system')
  const chip = (value: string | null, label: string) => {
    const on = active === value
    return (
      <button
        key={value ?? 'all'}
        type="button"
        onClick={() => onChange(value)}
        aria-pressed={on}
        className={`border-r border-border px-3 py-1.5 text-xs transition-colors ${
          on ? 'bg-input text-text' : 'text-text-secondary hover:bg-surface hover:text-text'
        }`}
      >
        {label}
      </button>
    )
  }
  return (
    <div className="flex flex-wrap border border-border bg-panel">
      {chip(null, t('data.catalog.category.all'))}
      {CATEGORY_ORDER.map((c) => chip(c, t(`data.catalog.category.${c}`)))}
    </div>
  )
}

function DatasetCardTile({ card }: { card: DatasetCard }) {
  const { t } = useTranslation('system')
  const cached = card.local === 'cached'
  const freqLabel = FREQ_KEY[card.freq] ? t(`data.catalog.freq.${FREQ_KEY[card.freq]}`) : card.freq
  return (
    <section
      className={`grid gap-2 border border-border bg-surface p-3 lg:grid-cols-[minmax(220px,0.9fr)_minmax(280px,1.2fr)_minmax(260px,1fr)] lg:items-start ${
        cached ? '' : 'opacity-60'
      }`}
    >
      <div>
        <h3 className="text-sm font-semibold text-text">{card.name_zh}</h3>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
          <StatusBadge tone="muted">{t(`data.catalog.category.${card.category}`)}</StatusBadge>
          <span className="tabular">
            {freqLabel} · {t('data.catalog.since', { year: card.history_start })}
          </span>
        </div>
      </div>

      {/* key + 一鍵複製（authoring 的主要動作：複製到策略碼裡） */}
      <div className="flex min-w-0 items-center gap-2">
        <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-text-secondary">
          {card.key}
        </code>
        <CopyButton value={card.key} label={t('data.catalog.copyKey')} />
      </div>

      <div className="text-xs text-text-secondary">
        <p>「{card.description}」</p>
        <div className="mt-2">
          {cached ? (
            <span className="inline-flex items-center gap-1 text-gain">
              <span aria-hidden>●</span> {t('data.catalog.local.cached')}
            </span>
          ) : (
            <StatusBadge tone="muted">{t('data.catalog.local.notCached')}</StatusBadge>
          )}
        </div>
      </div>

      {/* 狀態二：策略庫反向索引（XQ 沒有的差異化）；used_by 空則整列不顯示 */}
      {card.used_by.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-border/50 pt-2 lg:col-span-3">
          <span aria-hidden className="text-warning">
            ⚡
          </span>
          <span className="sr-only">{t('data.catalog.usedByLabel')}</span>
          {card.used_by.map((s) => (
            <span
              key={s}
              className="border border-border bg-input px-2 py-0.5 font-mono text-[11px] text-text-secondary"
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </section>
  )
}

export function DatasetCatalog() {
  const { t } = useTranslation('system')
  const q = useDatasets()
  const [category, setCategory] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  return (
    <div>
      {/* 控制列：搜尋 + 分類 chips（永遠顯示，即使過濾到空） */}
      <div className="mb-4 flex flex-col gap-3">
        <input
          className={inputCls}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('data.catalog.search')}
          aria-label={t('data.catalog.search')}
        />
        <CategoryChips active={category} onChange={setCategory} />
      </div>

      <QueryState
        q={q}
        resource={t('data.catalog.resource')}
        pendingLabel={t('data.catalog.pending')}
        emptyLabel={t('data.catalog.empty')}
      >
        {(cards: DatasetCard[]) => {
          const filtered = filterCards(cards, category, search)
          if (filtered.length === 0)
            return (
              <div className="border border-border bg-surface p-6 text-sm">
                <p className="text-text-secondary">{t('data.catalog.noMatch', { q: search })}</p>
                <p className="mt-1 text-xs text-text-muted">{t('data.catalog.noMatchHint')}</p>
              </div>
            )
          return (
            <div className="grid gap-2">
              {filtered.map((c) => (
                <DatasetCardTile key={c.key} card={c} />
              ))}
            </div>
          )
        }}
      </QueryState>
    </div>
  )
}
