/*
 * Decision action bar（sticky 底部）—— Keep / Archive / Rerun / Select Live OOS。
 * fixture 模式：純本地狀態（樂觀更新），顯眼「fixture 模式——尚未接後端」badge；
 * 按鈕觸發後本地標記選中的 decision，不送後端（Goal 4 candidate decision API 落地後改接
 * POST /research/candidates/{id}/decision）。Select Live OOS 依 recommendation 決定是否需 override 理由。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { DataSource } from '../../api/reportViewer'

type DecisionAction = 'keep' | 'archive' | 'rerun' | 'select_live_oos'

const ACTIONS: { action: DecisionAction; labelKey: string; primary?: boolean }[] = [
  { action: 'keep', labelKey: 'reportViewer.decision.keep' },
  { action: 'archive', labelKey: 'reportViewer.decision.archive' },
  { action: 'rerun', labelKey: 'reportViewer.decision.rerun' },
  { action: 'select_live_oos', labelKey: 'reportViewer.decision.selectLiveOos', primary: true },
]

export function DecisionActionBar({
  source,
  recommendationAction,
}: {
  source: DataSource
  /** verdict.recommendation.action（eligible_for_live_oos → Select Live OOS 免 override 理由）。 */
  recommendationAction: string
}) {
  const { t } = useTranslation('research')
  const [marked, setMarked] = useState<DecisionAction | null>(null)
  const eligible = recommendationAction === 'eligible_for_live_oos'

  return (
    <div className="sticky bottom-0 mt-3 rounded-lg border border-border bg-surface px-4 py-2">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-xs text-text-muted">{t('reportViewer.decision.title')}</span>

        {source === 'fixture' && (
          <StatusBadge tone="warning">
            <span aria-hidden>◆</span>
            {t('reportViewer.decision.fixtureBadge')}
          </StatusBadge>
        )}

        {marked && (
          <StatusBadge tone="gain">
            <span aria-hidden>✓</span>
            {t('reportViewer.decision.marked', { action: t(`reportViewer.decision.${camel(marked)}`) })}
          </StatusBadge>
        )}

        <div className="ml-auto flex flex-wrap gap-2">
          {ACTIONS.map((a) => {
            const needsOverride = a.action === 'select_live_oos' && !eligible
            return (
              <button
                key={a.action}
                type="button"
                data-testid={`decision-${a.action}`}
                onClick={() => setMarked(a.action)}
                title={needsOverride ? t('reportViewer.decision.reasonRequired') : undefined}
                className={
                  a.primary
                    ? 'rounded-pill bg-text px-4 py-1 font-medium text-base hover:opacity-90'
                    : 'rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text'
                }
              >
                {t(a.labelKey)}
                {needsOverride && <span className="ml-1 text-[11px]">*</span>}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/** select_live_oos → selectLiveOos（i18n key 用 camelCase）。 */
function camel(a: DecisionAction): string {
  return a.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
}
