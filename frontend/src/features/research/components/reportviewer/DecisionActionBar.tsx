/*
 * Decision action bar（sticky 底部）—— Keep / Archive / Rerun / Select Live OOS。
 * 與 Candidate Pool 共用 mutation hooks（useDecisionMutation / useSelectLiveOosMutation）：
 * - api 模式：真寫入 POST /research/candidates/{cand_<strategy>}/decision | /select-live-oos，
 *   成功 invalidate 候選池；失敗（400/409/422）顯示錯誤（bar 內或理由彈窗內，不靜默）。
 *   archive 與非 eligible 的 Select Live OOS 走 ReasonDialog 收 override 理由。
 * - fixture 模式：純本地標記（樂觀），顯眼「fixture 模式——尚未接後端」badge，不送後端。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { ReasonDialog } from '../candidates/ReasonDialog'
import { useDecisionMutation, useSelectLiveOosMutation } from '../../hooks/useCandidateMutations'
import { describeMutationError, type DecisionRequestBody } from '../../api/candidates'
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
  strategy,
  recommendation,
}: {
  source: DataSource
  /** verdict.recommendation.action（eligible_for_live_oos → Select Live OOS 免 override 理由）。 */
  recommendationAction: string
  /** 決策目標策略 → candidate_id（cand_<strategy>）；api 模式真寫入所需。 */
  strategy: string
  /** verdict.live_oos_recommendation（eligible / not_recommended / blocked）；fixture 無此欄 → undefined。 */
  recommendation?: string | null
}) {
  const { t } = useTranslation('research')
  const decisionM = useDecisionMutation()
  const selectM = useSelectLiveOosMutation()
  const [marked, setMarked] = useState<DecisionAction | null>(null)
  const [pending, setPending] = useState<DecisionAction | null>(null)
  const [pendingError, setPendingError] = useState<string | null>(null)
  const [barError, setBarError] = useState<string | null>(null)

  const isApi = source === 'api'
  const candidateId = `cand_${strategy}`
  // recommendation 缺（fixture）時退回以 recommendationAction 判斷 eligibility。
  const eligible =
    recommendation != null
      ? recommendation === 'eligible'
      : recommendationAction === 'eligible_for_live_oos'
  const submitting = decisionM.isPending || selectM.isPending

  const reasonNeeded = (a: DecisionAction) =>
    a === 'archive' || (a === 'select_live_oos' && !eligible)

  const runApi = (a: DecisionAction, reason: string | undefined, fromDialog: boolean) => {
    const onError = (err: unknown) => {
      const message = describeMutationError(err)
      if (fromDialog) setPendingError(message)
      else setBarError(message)
    }
    const onSuccess = () => {
      setMarked(a)
      setBarError(null)
      if (fromDialog) {
        setPending(null)
        setPendingError(null)
      }
    }

    if (a === 'select_live_oos') {
      selectM.mutate(
        { candidateId, body: { reason, override: !eligible, observation_kind: 'paper_replay' } },
        { onSuccess, onError },
      )
      return
    }
    const body: DecisionRequestBody = { action: a, reason }
    if (a === 'keep') body.label = 'promising'
    decisionM.mutate({ candidateId, body }, { onSuccess, onError })
  }

  const onClick = (a: DecisionAction) => {
    setBarError(null)
    if (!isApi) {
      setMarked(a) // fixture：純本地標記
      return
    }
    if (reasonNeeded(a)) {
      setPendingError(null)
      setPending(a)
    } else {
      runApi(a, undefined, false)
    }
  }

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
            {t(isApi ? 'reportViewer.decision.saved' : 'reportViewer.decision.marked', {
              action: t(`reportViewer.decision.${camel(marked)}`),
            })}
          </StatusBadge>
        )}

        {barError && (
          <StatusBadge tone="error">
            <span aria-hidden>✕</span>
            {t('reportViewer.decision.error', { detail: barError })}
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
                onClick={() => onClick(a.action)}
                disabled={submitting}
                title={needsOverride ? t('reportViewer.decision.reasonRequired') : undefined}
                className={
                  a.primary
                    ? 'rounded-pill bg-text px-4 py-1 font-medium text-base hover:opacity-90 disabled:opacity-40'
                    : 'rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text disabled:opacity-40'
                }
              >
                {t(a.labelKey)}
                {needsOverride && <span className="ml-1 text-[11px]">*</span>}
              </button>
            )
          })}
        </div>
      </div>

      {pending && (
        <ReasonDialog
          action={pending}
          strategy={strategy}
          recommendationLabel={
            pending === 'select_live_oos' && recommendation != null
              ? t(`candidates.recommendation.${recommendation}`, { defaultValue: recommendation })
              : undefined
          }
          error={pendingError ?? undefined}
          submitting={submitting}
          onSubmit={(reason) => runApi(pending, reason, true)}
          onCancel={() => {
            setPending(null)
            setPendingError(null)
          }}
        />
      )}
    </div>
  )
}

/** select_live_oos → selectLiveOos（i18n key 用 camelCase）。 */
function camel(a: DecisionAction): string {
  return a.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
}
