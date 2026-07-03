/*
 * 五張 scorecard 摘要網格 —— Profitability / Risk / Risk-Adjusted / Win Rate / Liquidity。
 * RWD：mobile 直向堆疊（grid-cols-1）→ sm 2 欄 → xl 5 欄，無文字重疊（UX 驗收 #4）。
 * 點卡 → 選中對應 sheet tab（active 狀態上移）。
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
    <section className="mb-3">
      <h2 className="mb-2 text-[18px] font-semibold">{t('reportViewer.scorecard.title')}</h2>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-5">
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
