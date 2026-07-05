/*
 * Candidate Pool blotter toolbar：狀態 chips（含「全部」）+ 文字搜尋（策略名 / hypothesis）
 * + 已封存切換。這裡是研究決策流的篩選台，不做卡片式瀏覽器。
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
    <div className="mb-3 border border-border bg-panel">
      <div className="flex flex-col gap-2 border-b border-border px-3 py-2 lg:flex-row lg:items-center">
        <input
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder={t('candidates.filter.searchPlaceholder')}
          aria-label={t('candidates.filter.searchPlaceholder')}
          className="h-8 w-full border border-border bg-base px-3 font-mono text-xs text-text placeholder:text-text-muted focus:border-info focus:outline-none lg:max-w-md"
        />

        <label className="inline-flex cursor-pointer items-center gap-2 text-xs uppercase tracking-[0.12em] text-text-secondary lg:ml-auto">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => onToggleArchived(e.target.checked)}
            className="accent-info"
          />
          {t('candidates.filter.showArchived', { n: archivedCount })}
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-1 px-3 py-2">
        {chips.map((chip) => {
          const isActive = chip.key === active
          const tone = chip.key === 'all' ? 'muted' : candidateStateTone(chip.key)
          return (
            <button
              key={chip.key}
              onClick={() => onSelect(chip.key)}
              aria-pressed={isActive}
              className={[
                'inline-flex h-7 items-center gap-1 border px-2 font-mono text-[11px] uppercase tracking-[0.08em]',
                isActive ? 'border-info bg-input text-text' : 'border-border text-text-secondary hover:border-border-strong hover:text-text',
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
      </div>
    </div>
  )
}
