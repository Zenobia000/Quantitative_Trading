/*
 * Candidate Pool（/research/candidates）—— 半自動決策主戰場（rebuild Goal 6）。
 * 每個評測結果（含壞 / 負向 / 資料問題）都留存為候選；人在此 Keep / Archive / Rerun / Select Live OOS。
 * fixture-first：先打 GET /research/candidates，失敗 fallback 打包契約範例並明示資料來源。
 * Deployment/promote 非主要動作（不放 promote 鈕）；部署判決僅以資訊態呈現。
 */
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'
import { useCandidatePool } from '../hooks/useCandidatePool'
import { useDecisionMutation, useSelectLiveOosMutation } from '../hooks/useCandidateMutations'
import { CandidateCard } from '../components/candidates/CandidateCard'
import { CandidateFilters, type StateChip, type StateFilter } from '../components/candidates/CandidateFilters'
import { ReasonDialog } from '../components/candidates/ReasonDialog'
import { applyDecision, reasonRequired, type CandidateAction } from '../components/candidates/candidateDisplay'
import { describeMutationError, type DecisionRequestBody, type Candidate, type CandidateState } from '../api/candidates'

/** chip 排序（archived 不入 chip，由切換開關掌管）。 */
const STATE_ORDER: CandidateState[] = [
  'promising',
  'live_oos_selected',
  'live_oos_running',
  'live_oos_done',
  'weak',
  'triaged',
  'draft',
  'negative',
  'data_issue',
  'deploy_blocked',
  'deployable',
]

interface Pending {
  candidate: Candidate
  action: CandidateAction
}

export function CandidatePoolPage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const query = useCandidatePool()
  const decisionM = useDecisionMutation()
  const selectM = useSelectLiveOosMutation()

  // fixture-mode 本地樂觀更新 overlay（candidate_id → 套用決策後的新 Candidate）。
  const [overrides, setOverrides] = useState<Record<string, Candidate>>({})
  const [pending, setPending] = useState<Pending | null>(null)
  // api 模式 mutation 錯誤：dialog 內（需理由的動作）與頁面 banner（免理由的動作）兩處呈現，不靜默。
  const [pendingError, setPendingError] = useState<string | null>(null)
  const [pageError, setPageError] = useState<{ strategy: string; message: string } | null>(null)
  const [active, setActive] = useState<StateFilter>('all')
  const [search, setSearch] = useState('')
  const [showArchived, setShowArchived] = useState(false)

  const source = query.data?.source
  const isApi = source === 'api'
  const submitting = decisionM.isPending || selectM.isPending
  const base = query.data?.candidates ?? []

  // base + 本地 overlay。
  const merged = useMemo(
    () => base.map((c) => overrides[c.candidate_id] ?? c),
    [base, overrides],
  )

  // 1) 文字搜尋（策略名 / hypothesis）。
  const bySearch = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return merged
    return merged.filter(
      (c) => c.strategy.toLowerCase().includes(q) || c.hypothesis.toLowerCase().includes(q),
    )
  }, [merged, search])

  // 2) chips 來源 = 搜尋後套 archived 規則（archived 預設隱藏）。
  const chipSource = useMemo(
    () => (showArchived ? bySearch : bySearch.filter((c) => c.state !== 'archived')),
    [bySearch, showArchived],
  )
  const archivedCount = useMemo(
    () => bySearch.filter((c) => c.state === 'archived').length,
    [bySearch],
  )

  const chips = useMemo<StateChip[]>(() => {
    const counts = new Map<CandidateState, number>()
    for (const c of chipSource) counts.set(c.state, (counts.get(c.state) ?? 0) + 1)
    const stateChips = STATE_ORDER.filter((s) => counts.has(s)).map((s) => ({
      key: s as StateFilter,
      count: counts.get(s) ?? 0,
    }))
    return [{ key: 'all', count: chipSource.length }, ...stateChips]
  }, [chipSource])

  // 3) state chip 過濾 → 可見卡。
  const visible = useMemo(
    () => (active === 'all' ? chipSource : chipSource.filter((c) => c.state === active)),
    [chipSource, active],
  )

  const closeDialog = () => {
    setPending(null)
    setPendingError(null)
  }

  // fixture 模式：本地樂觀 overlay（既有行為，不打後端）。
  const applyLocal = (candidate: Candidate, action: CandidateAction, reason?: string) => {
    const current = overrides[candidate.candidate_id] ?? candidate
    setOverrides((prev) => ({
      ...prev,
      [candidate.candidate_id]: applyDecision(current, action, reason),
    }))
    setPending(null)
  }

  // api 模式：真 mutation（decision / select-live-oos）→ 成功 invalidate 重抓；失敗顯示錯誤（不靜默）。
  const runApiMutation = (
    candidate: Candidate,
    action: CandidateAction,
    reason: string | undefined,
    fromDialog: boolean,
  ) => {
    const onError = (err: unknown) => {
      const message = describeMutationError(err)
      if (fromDialog) setPendingError(message)
      else setPageError({ strategy: candidate.strategy, message })
    }
    const onSuccess = () => {
      setPageError(null)
      if (fromDialog) closeDialog()
    }

    if (action === 'select_live_oos') {
      const override = candidate.live_oos_recommendation !== 'eligible'
      selectM.mutate(
        { candidateId: candidate.candidate_id, body: { reason, override, observation_kind: 'paper_replay' } },
        { onSuccess, onError },
      )
      return
    }
    // keep / archive / rerun → POST /decision（keep 必帶 label；本 MVP UI 的 keep 記為 promising）。
    const body: DecisionRequestBody = { action, reason }
    if (action === 'keep') body.label = 'promising'
    decisionM.mutate({ candidateId: candidate.candidate_id, body }, { onSuccess, onError })
  }

  const execute = (
    candidate: Candidate,
    action: CandidateAction,
    reason: string | undefined,
    fromDialog: boolean,
  ) => {
    if (isApi) runApiMutation(candidate, action, reason, fromDialog)
    else applyLocal(candidate, action, reason)
  }

  const onAction = (candidate: Candidate, action: CandidateAction) => {
    setPageError(null)
    if (reasonRequired(candidate, action)) {
      setPendingError(null)
      setPending({ candidate, action })
    } else {
      execute(candidate, action, undefined, false)
    }
  }

  return (
    <div>
      <PageHeader
        title={t('candidates.title')}
        route="/research/candidates"
        subtitle={t('candidates.subtitle')}
      />

      {/* data source badge —— fixture 模式明示尚未接後端 */}
      {source === 'fixture' ? (
        <div className="mb-3 flex flex-col gap-1 rounded-lg border border-warning/40 bg-surface px-4 py-2.5">
          <div className="flex items-center gap-2">
            <StatusBadge tone="warning">{t('candidates.dataSource.fixture')}</StatusBadge>
          </div>
          <p className="text-xs text-text-muted">{t('candidates.dataSource.fixtureHint')}</p>
        </div>
      ) : source === 'api' ? (
        <div className="mb-3">
          <StatusBadge tone="muted">{t('candidates.dataSource.live')}</StatusBadge>
        </div>
      ) : null}

      {/* api 模式免理由動作的 mutation 失敗（如 illegal transition）→ 頁面 banner，不靜默 */}
      {pageError && (
        <div
          role="alert"
          className="mb-3 rounded-lg border border-error/50 bg-surface px-4 py-2.5 text-sm text-error"
        >
          {t('candidates.error.actionFailed', {
            strategy: pageError.strategy,
            detail: pageError.message,
          })}
        </div>
      )}

      {query.isLoading ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <SkeletonRows rows={4} cols={4} />
        </div>
      ) : query.isError ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm">
          <p className="text-error">
            {t('errors:load.failed', { resource: t('candidates.resource'), detail: errText(query.error) })}
          </p>
          <button
            onClick={() => query.refetch()}
            className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
          >
            {t('common:action.retry')}
          </button>
        </div>
      ) : merged.length === 0 ? (
        <FirstRunEmptyState
          headline={t('candidates.empty.headline')}
          subtitle={t('candidates.empty.subtitle')}
          ctaLabel={t('candidates.empty.cta')}
          onCta={() => navigate('/research/runs/new')}
        />
      ) : (
        <>
          <CandidateFilters
            chips={chips}
            active={active}
            onSelect={setActive}
            query={search}
            onQuery={setSearch}
            showArchived={showArchived}
            onToggleArchived={setShowArchived}
            archivedCount={archivedCount}
          />

          {visible.length === 0 ? (
            <div className="rounded-lg border border-border bg-surface p-6 text-sm text-text-muted">
              {t('candidates.filter.noMatch')}
            </div>
          ) : (
            <div className="grid gap-2 lg:grid-cols-2">
              {visible.map((c) => (
                <CandidateCard
                  key={c.candidate_id}
                  candidate={c}
                  locallyModified={c.candidate_id in overrides}
                  onAction={(action) => onAction(c, action)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {pending && (
        <ReasonDialog
          action={pending.action}
          strategy={pending.candidate.strategy}
          recommendationLabel={
            pending.action === 'select_live_oos'
              ? t(`candidates.recommendation.${pending.candidate.live_oos_recommendation}`)
              : undefined
          }
          error={pendingError ?? undefined}
          submitting={submitting}
          onSubmit={(reason) => execute(pending.candidate, pending.action, reason, true)}
          onCancel={closeDialog}
        />
      )}
    </div>
  )
}
