/*
 * DatasetCatalog — 資料字典 blotter（authoring-first）。
 *
 * 定位：這是「策略作者的資料字典」——
 * 搜有什麼資料可以寫策略、複製 key、看本地有無與取數方式。不是快取運維儀表板，
 * 故不呈現 staleness / coverage / manifest。
 *
 * 狀態唯二：本地已有(cached)/未下載(not_cached) 的二元、與 runtime fetch。
 * 分類 chip + 搜尋（比對 key + name_zh + description）全在前端做，資料一次拉全量。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { CopyButton } from '@/components/CopyButton'
import { QueryState } from '@/features/monitor/components'
import { useDatasets, useUniverses, useTriggerIngest, useIngestStatus } from '../hooks/useSystem'
import type { DatasetCard, UniverseRow } from '../hooks/useSystem'

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

function UniverseScope({
  selectedId,
  onSelect,
}: {
  selectedId: string
  onSelect: (universeId: string) => void
}) {
  const { t } = useTranslation('system')
  const q = useUniverses()

  return (
    <QueryState q={q} resource={t('data.catalog.universe.resource')} pendingLabel={t('data.catalog.universe.pending')} emptyLabel={t('data.catalog.universe.empty')}>
      {(rows: UniverseRow[]) => {
        const selected = rows.find((r) => r.id === selectedId) ?? rows[0] ?? null
        const span = selected ? `${selected.span_start ?? 'n/a'} → ${selected.span_end ?? 'n/a'}` : t('data.catalog.universe.defaultSpan')
        return (
          <div className="border border-border bg-panel px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-2 text-xs text-text-muted">
                {t('data.catalog.universe.label')}
                <select
                  className="border border-border bg-base px-2 py-1 text-xs text-text"
                  value={selected?.id ?? ''}
                  onChange={(e) => onSelect(e.target.value)}
                >
                  <option value="">{t('data.catalog.universe.default')}</option>
                  {rows.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.symbols_count})
                    </option>
                  ))}
                </select>
              </label>
              <span className="text-xs text-text-muted">
                {t('data.catalog.universe.span')}: <span className="font-mono text-text-secondary">{span}</span>
              </span>
              {selected && (
                <span className="text-xs text-text-muted">
                  {t('data.catalog.universe.symbols', { n: selected.symbols_count })}
                </span>
              )}
            </div>
          </div>
        )
      }}
    </QueryState>
  )
}

/** finlab 取數用法（教「怎麼用這個 key」，非只複製）：`data.get('<key>')`。 */
function usageSnippet(key: string): string {
  return `data.get('${key}')`
}

/**
 * 一張資料卡 = 收合列（`<details>`）。收起僅一行（名稱 · 分類 · 頻率 · 本地燈），
 * 展開才顯示 API 用法 + 說明；bundle-backed 且未快取時，提供一鍵補表。
 */
function DatasetCardTile({
  card,
  onDownload,
  downloadDisabled,
  downloadLabel,
}: {
  card: DatasetCard
  onDownload?: (card: DatasetCard) => void
  downloadDisabled?: boolean
  downloadLabel?: string
}) {
  const { t } = useTranslation('system')
  const cached = card.local === 'cached'
  const bundleBacked = card.bundle_backed
  const freqLabel = FREQ_KEY[card.freq] ? t(`data.catalog.freq.${FREQ_KEY[card.freq]}`) : card.freq
  const usage = usageSnippet(card.key)
  return (
    <details className={`group border border-border bg-surface ${bundleBacked && !cached ? 'opacity-70' : ''}`}>
      <summary className="flex cursor-pointer select-none flex-wrap items-center gap-2 px-3 py-2 marker:text-text-muted">
        <span className="text-sm font-semibold text-text">{card.name_zh}</span>
        <StatusBadge tone="muted">{t(`data.catalog.category.${card.category}`)}</StatusBadge>
        <span className="tabular text-xs text-text-muted">
          {freqLabel} · {t('data.catalog.since', { year: card.history_start })}
        </span>
        <span className="ml-auto text-xs">
          {!bundleBacked ? (
            <StatusBadge tone="muted">{t('data.catalog.local.runtimeOnly')}</StatusBadge>
          ) : cached ? (
            <span className="inline-flex items-center gap-1 text-gain">
              <span aria-hidden>●</span> {t('data.catalog.local.cached')}
            </span>
          ) : (
            <StatusBadge tone="muted">{t('data.catalog.local.notCached')}</StatusBadge>
          )}
        </span>
      </summary>

      <div className="grid gap-2 border-t border-border/60 px-3 py-3 text-xs text-text-secondary">
        {/* API 用法（authoring 的主要動作：複製整段取數呼叫到策略碼裡） */}
        <div>
          <div className="mb-1 text-[11px] uppercase tracking-wide text-text-muted">
            {t('data.catalog.usage')}
          </div>
          <div className="flex min-w-0 items-center gap-2">
            <code className="flex-1 overflow-x-auto whitespace-nowrap rounded bg-base px-2 py-1 font-mono text-text-secondary">
              {usage}
            </code>
            <CopyButton value={usage} label={t('data.catalog.copyUsage')} />
          </div>
          <a
            href="https://ai.finlab.tw/database"
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-[11px] text-text-muted underline-offset-2 hover:text-text hover:underline"
          >
            {t('data.catalog.docLink')}
          </a>
        </div>
        <p>「{card.description}」</p>
        {bundleBacked && !cached && onDownload && (
          <div className="pt-1">
            <button
              type="button"
              className="border border-text/30 bg-text px-3 py-1 text-xs font-medium text-base disabled:opacity-50"
              onClick={() => onDownload(card)}
              disabled={downloadDisabled}
            >
              {downloadLabel ?? t('data.catalog.download')}
            </button>
          </div>
        )}
      </div>
    </details>
  )
}

export function DatasetCatalog() {
  const { t } = useTranslation('system')
  const q = useDatasets()
  const trigger = useTriggerIngest()
  const [jobId, setJobId] = useState<string | null>(null)
  const status = useIngestStatus(jobId)
  const [category, setCategory] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [universeId, setUniverseId] = useState('')

  const selectedUniverseQ = useUniverses()
  const selectedUniverse = selectedUniverseQ.data?.data?.find((u) => u.id === universeId) ?? selectedUniverseQ.data?.data?.[0] ?? null
  const onDownload = () => {
    if (!selectedUniverse) return
    const start = selectedUniverse.span_start ?? ''
    const end = selectedUniverse.span_end ?? ''
    if (!start || !end) return
    trigger.mutate(
      {
        universe: selectedUniverse.id,
        start,
        end,
        source: 'finlab',
      },
      { onSuccess: (res) => setJobId(res.data.job_id) },
    )
  }

  return (
    <div>
      {/* 控制列：搜尋 + 分類 chips（永遠顯示，即使過濾到空） */}
      <div className="mb-4 flex flex-col gap-3">
        <UniverseScope selectedId={universeId} onSelect={setUniverseId} />
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
            <>
              {jobId && (
                <div className="mb-3 border border-border bg-panel px-3 py-2 text-xs text-text-secondary">
                  {status.isError ? (
                    <span className="text-error">{t('data.job.error', { jobId, detail: 'download job failed' })}</span>
                  ) : (
                    <>
                      {t('data.job.label')} <span className="text-text">{jobId}</span> · {t('data.job.statusLabel')}{' '}
                      <span className="font-medium text-text">{status.data?.data?.status ?? 'queued'}</span>
                      {status.data?.data?.result && (
                        <span>
                          {' '}
                          · {t('data.ingest.result', {
                            ok: status.data.data.result.ok?.length ?? 0,
                            failed: status.data.data.result.failed?.length ?? 0,
                          })}
                        </span>
                      )}
                    </>
                  )}
                </div>
              )}
              <div className="grid gap-2">
                {filtered.map((c) => (
                  <DatasetCardTile
                    key={c.key}
                    card={c}
                    onDownload={onDownload}
                    downloadDisabled={!selectedUniverse || !selectedUniverse.span_start || !selectedUniverse.span_end || trigger.isPending}
                    downloadLabel={t('data.catalog.download')}
                  />
                ))}
              </div>
            </>
          )
        }}
      </QueryState>
    </div>
  )
}
