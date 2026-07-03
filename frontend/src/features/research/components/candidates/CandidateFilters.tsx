/*
 * Candidate Pool 過濾列：狀態 chips（含「全部」）+ 文字搜尋（策略名 / hypothesis）
 * + 已封存切換（archived 預設隱藏但可切換顯示；acceptance：bad/archived 仍可發現）。
 * 純受控元件；chips 由頁面依實際資料派生（避免死 chip）。
 */
import { useTranslation } from 'react-i18next'
import { candidateStateTone } from './candidateDisplay'
import type { CandidateState } from '../../api/candidates'

export type StateFilter = CandidateState | 'all'

export interface StateChip {
  key: StateFilter
  count: number
}

export function CandidateFilters({
  chips,
  active,
  onSelect,
  query,
  onQuery,
  showArchived,
  onToggleArchived,
  archivedCount,
}: {
  chips: StateChip[]
  active: StateFilter
  onSelect: (s: StateFilter) => void
  query: string
  onQuery: (q: string) => void
  showArchived: boolean
  onToggleArchived: (v: boolean) => void
  archivedCount: number
}) {
  const { t } = useTranslation('research')
  const label = (key: StateFilter) =>
    key === 'all' ? t('candidates.filter.all') : t(`candidates.state.${key}`, { defaultValue: key })

  return (
    <div className="mb-3 flex flex-col gap-3">
      {/* search */}
      <input
        type="search"
        value={query}
        onChange={(e) => onQuery(e.target.value)}
        placeholder={t('candidates.filter.searchPlaceholder')}
        aria-label={t('candidates.filter.searchPlaceholder')}
        className="w-full rounded-md border border-border bg-input px-3 py-1.5 text-sm text-text placeholder:text-text-muted focus:border-text/40 focus:outline-none sm:max-w-sm"
      />

      {/* state chips + archived toggle */}
      <div className="flex flex-wrap items-center gap-1.5">
        {chips.map((chip) => {
          const isActive = chip.key === active
          const tone = chip.key === 'all' ? 'muted' : candidateStateTone(chip.key)
          return (
            <button
              key={chip.key}
              onClick={() => onSelect(chip.key)}
              aria-pressed={isActive}
              className={[
                'inline-flex items-center gap-1 rounded-pill border px-2.5 py-0.5 text-xs',
                isActive ? 'border-text/50 bg-input text-text' : 'border-border text-text-secondary hover:text-text',
                !isActive && tone === 'gain' ? 'text-gain' : '',
                !isActive && tone === 'warning' ? 'text-warning' : '',
                !isActive && tone === 'loss' ? 'text-loss' : '',
                !isActive && tone === 'error' ? 'text-error' : '',
              ].join(' ')}
            >
              <span>{label(chip.key)}</span>
              <span className="font-mono tabular text-text-muted">{chip.count}</span>
            </button>
          )
        })}
        <label className="ml-auto inline-flex cursor-pointer items-center gap-1.5 text-xs text-text-secondary">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => onToggleArchived(e.target.checked)}
            className="accent-text"
          />
          {t('candidates.filter.showArchived', { n: archivedCount })}
        </label>
      </div>
    </div>
  )
}
