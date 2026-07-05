/*
 * 分支實驗 section（Goal 9）—— 住策略資產詳情頁（不開新 route，IA spec 列 deferred detail）。
 *
 * 列該策略的分支（config delta chips / origin / status）+ evaluate（quick_triage 同步）+ compare
 * （展開後端 delta 表）+ 手動建分支彈窗。分支從候選最新評測 fork（parentEvaluationId）；無候選 →
 * 建分支按鈕 disabled 附提示（先評估才有 parent）。誠實態：overlay-only 分支標「不可評測」不留無說明佔位。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { SkeletonRows } from '@/components/Skeleton'
import { ApiError } from '@/services/http'
import { useErrorText } from '@/i18n/useErrorText'
import { useBranches, useCreateBranch, useEvaluateBranch } from '../../hooks/useBranches'
import { describeMutationError } from '../../api/candidates'
import type { BranchExperiment, ConfigDeltaEntry } from '../../api/branches'
import { BranchCreateDialog } from './BranchCreateDialog'
import { BranchCompareTable } from './BranchCompareTable'

const ORIGIN_TONE = { simulation: 'warning', manual: 'muted', report_finding: 'muted' } as const

function DeltaChips({ delta }: { delta: ConfigDeltaEntry[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {delta.map((d) => (
        <span
          key={d.key}
          className="rounded-md border border-border bg-surface-raised px-2 py-0.5 font-mono text-[11px] text-text-secondary"
        >
          {d.key}: {String(d.from ?? '—')} → {String(d.to)}
        </span>
      ))}
    </div>
  )
}

function BranchRow({
  branch,
  onEvaluate,
  evaluating,
}: {
  branch: BranchExperiment
  onEvaluate: (id: string) => void
  evaluating: boolean
}) {
  const { t } = useTranslation('research')
  const [showCompare, setShowCompare] = useState(false)
  const isDraft = branch.status === 'draft'

  return (
    <li className="flex flex-col gap-2 px-4 py-3" data-testid="branch-row">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge tone={branch.status === 'evaluated' ? 'gain' : 'muted'}>
          {t(`branches.status.${branch.status}`)}
        </StatusBadge>
        <StatusBadge tone={ORIGIN_TONE[branch.origin]}>{t(`branches.origin.${branch.origin}`)}</StatusBadge>
        <span className="font-mono text-[11px] text-text-muted">{branch.branch_id}</span>
      </div>

      <DeltaChips delta={branch.config_delta} />
      {branch.note && <p className="text-xs text-text-muted">{branch.note}</p>}

      <div className="flex flex-wrap items-center gap-3 text-xs">
        {isDraft && branch.applies_to_rerun && (
          <button
            onClick={() => onEvaluate(branch.branch_id)}
            disabled={evaluating}
            data-testid="branch-evaluate"
            className="rounded-md border border-text/40 px-3 py-1 font-medium text-text hover:bg-input disabled:opacity-40"
          >
            {evaluating ? t('branches.evaluating') : t('branches.evaluate')}
          </button>
        )}
        {isDraft && !branch.applies_to_rerun && (
          <span className="text-text-muted" data-testid="branch-not-evaluable">
            <span aria-hidden>⊘ </span>
            {t('branches.notEvaluable')}
          </span>
        )}
        {branch.status === 'evaluated' && (
          <button
            onClick={() => setShowCompare((v) => !v)}
            aria-expanded={showCompare}
            data-testid="branch-compare-toggle"
            className="text-text-secondary underline-offset-2 hover:text-text hover:underline"
          >
            {t('branches.compareToggle')}
          </button>
        )}
      </div>

      {showCompare && branch.status === 'evaluated' && <BranchCompareTable branchId={branch.branch_id} />}
    </li>
  )
}

export function BranchExperimentsSection({
  strategy,
  parentEvaluationId,
  configFields,
}: {
  strategy: string
  /** 候選最新評測 id（分支 parent）；null = 尚無評測 → 不能 fork。 */
  parentEvaluationId: string | null
  /** parent 策略 config_model 欄位（手動 fork 可選 key）。 */
  configFields: string[]
}) {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const query = useBranches(strategy)
  const createM = useCreateBranch()
  const evaluateM = useEvaluateBranch()
  const [dialogOpen, setDialogOpen] = useState(false)

  const canCreate = !!parentEvaluationId && configFields.length > 0
  const branches = query.data ?? []

  const submitCreate = (delta: ConfigDeltaEntry[], note: string) => {
    if (!parentEvaluationId) return
    createM.mutate(
      { parent_evaluation_id: parentEvaluationId, config_delta: delta, origin: 'manual', note: note || undefined },
      { onSuccess: () => setDialogOpen(false) },
    )
  }

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface" data-testid="branch-section">
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-2">
        <span className="text-xs uppercase tracking-wide text-text-muted">{t('branches.title')}</span>
        <button
          onClick={() => setDialogOpen(true)}
          disabled={!canCreate}
          data-testid="branch-create-open"
          title={!canCreate ? t('branches.createNeedsParent') : undefined}
          className="ml-auto rounded-md border border-text/40 px-3 py-1 text-xs font-medium text-text hover:bg-input disabled:opacity-40"
        >
          {t('branches.createCta')}
        </button>
      </div>

      {evaluateM.isError && (
        <p className="px-4 pt-2 text-xs text-error" data-testid="branch-evaluate-error">
          {t('branches.evaluateError', {
            detail:
              evaluateM.error instanceof ApiError ? describeMutationError(evaluateM.error) : String(evaluateM.error),
          })}
        </p>
      )}

      {query.isLoading ? (
        <div className="p-4">
          <SkeletonRows rows={2} cols={3} />
        </div>
      ) : query.isError ? (
        <div className="flex flex-wrap items-center gap-3 p-4 text-xs text-text-muted">
          <span>{t('branches.unavailable', { detail: errText(query.error) })}</span>
          <button
            onClick={() => query.refetch()}
            className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
          >
            {t('common:action.retry')}
          </button>
        </div>
      ) : branches.length === 0 ? (
        <div className="p-6 text-sm">
          <p className="text-text-muted">{t('branches.empty')}</p>
          {!parentEvaluationId && <p className="mt-1 text-xs text-text-muted">{t('branches.createNeedsParent')}</p>}
        </div>
      ) : (
        <ul className="divide-y divide-border/60">
          {branches.map((b) => (
            <BranchRow
              key={b.branch_id}
              branch={b}
              onEvaluate={(id) => evaluateM.mutate(id)}
              evaluating={evaluateM.isPending && evaluateM.variables === b.branch_id}
            />
          ))}
        </ul>
      )}

      {dialogOpen && (
        <BranchCreateDialog
          strategy={strategy}
          configFields={configFields}
          submitting={createM.isPending}
          error={
            createM.isError
              ? createM.error instanceof ApiError
                ? describeMutationError(createM.error)
                : String(createM.error)
              : undefined
          }
          onSubmit={submitCreate}
          onCancel={() => {
            setDialogOpen(false)
            createM.reset()
          }}
        />
      )}
    </section>
  )
}
