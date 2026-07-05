/*
 * Scorecard ledger summary —— Profitability / Risk / Risk-Adjusted / Win Rate / Liquidity。
 * 點列 → 選中對應 sheet tab（active 狀態上移）。
 */
import { useTranslation } from 'react-i18next'
import type { Scorecard } from '../../api/reportViewer'
import { ScorecardCard } from './ScorecardCard'

export function ScorecardGrid({
  scorecards,
  activeCategory,
  onSelect,
}: {
  scorecards: Scorecard[]
  activeCategory: string
  onSelect: (category: string) => void
}) {
  const { t } = useTranslation('research')
  return (
    <section className="mb-3 border border-border bg-panel">
      <div className="border-b border-border px-3 py-2">
        <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
          {t('reportViewer.scorecard.title')}
        </h2>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5">
        {scorecards.map((sc) => (
          <ScorecardCard
            key={sc.category}
            scorecard={sc}
            active={sc.category === activeCategory}
            onSelect={() => onSelect(sc.category)}
          />
        ))}
      </div>
    </section>
  )
}
