/*
 * Promote（UI route /deploy/promote/:strategyId，rebuild IA §1.3 移入 Deployment zone）— 不可逆晉升狀態機（後端 8.H.7 / S3）。
 * 接真實 GET /research/promote/{id}（current stage + gates）、POST（前進一階，draft→paper→live）、
 * GET /audit（immutable trail）。stepper 顯示已達階段，advance 鈕觸發 mutation。
 * 前端防線（此工作包）：無 gate PASS 證據時 disable advance —— gate 證據取自 strategy roster
 * （GET /research/strategies）的 validation_status（由各 run 的 gate_status 投影）。後端硬防線屬另一工作包。
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { usePromoteAudit, usePromoteState, useAdvancePromote } from '../hooks/usePromote'
import { useStrategies } from '../hooks/useStrategies'
import { PageHeader } from '@/components/PageHeader'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { EnumBadge } from '@/components/EnumBadge'
import { useEnumLabel } from '@/i18n/useEnumLabel'
import { useErrorText } from '@/i18n/useErrorText'
import { ApiError } from '@/services/http'

const STAGES = ['draft', 'paper', 'live'] as const

/** 本地化階段名（stepper 標籤用純文字，不套 badge）。 */
function StageName({ value }: { value?: string | null }) {
  const { label } = useEnumLabel('stage', value)
  return <>{label}</>
}

export function PromotePage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const { strategyId } = useParams<{ strategyId: string }>()
  const sid = strategyId ?? ''
  const state = usePromoteState(sid)
  const audit = usePromoteAudit(sid)
  const advance = useAdvancePromote(sid)
  const roster = useStrategies()
  const [note, setNote] = useState('')

  const stage = state.data?.data?.stage ?? 'draft'
  const gates = state.data?.data?.gates ?? STAGES.map((s, i) => ({ stage: s, reached: i === 0 }))
  const curIdx = STAGES.indexOf(stage as (typeof STAGES)[number])
  const nextStage = curIdx >= 0 && curIdx < STAGES.length - 1 ? STAGES[curIdx + 1] : null
  const nextStageLabel = useEnumLabel('stage', nextStage).label

  // gate PASS 前置：策略須有 IS PASS 的 run（roster validation_status==='is_pass'）方可晉升。
  const rosterRows = roster.data?.data
  const strategyRow = Array.isArray(rosterRows) ? rosterRows.find((r) => r.strategy_id === sid) : undefined
  const gatePassed = strategyRow?.validation_status === 'is_pass'
  const canAdvance = !advance.isPending && gatePassed

  return (
    <div>
      <PageHeader
        title={t('promote.title')}
        route={`/deploy/promote/${sid}`}
        subtitle={t('promote.subtitle')}
        back={{ label: t('promote.back'), to: '/research/strategies' }}
      />

      {/* stepper */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">{sid || '—'}</h2>
          <EnumBadge family="stage" value={stage} />
        </div>
        {state.isLoading ? (
          <SkeletonRows rows={3} cols={2} />
        ) : (
          <ol className="flex items-center gap-2">
            {gates.map((g, i) => (
              <li key={g.stage} className="flex items-center gap-2">
                <span
                  className={
                    'flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm ' +
                    (g.reached
                      ? 'border-border bg-surface-raised text-text'
                      : 'border-border/60 text-text-muted')
                  }
                >
                  <StatusBadge tone={g.reached ? 'gain' : 'muted'}>{g.reached ? '✓' : i + 1}</StatusBadge>
                  <StageName value={g.stage} />
                </span>
                {i < gates.length - 1 && <span className="text-text-muted">→</span>}
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* advance control */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-2 text-[18px] font-semibold">{t('promote.advance.title')}</h2>
        {nextStage ? (
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t('promote.advance.notePlaceholder')}
                className="min-w-[240px] flex-1 rounded-md border border-border bg-surface-raised px-3 py-1.5"
              />
              <button
                onClick={() => advance.mutate({ to_stage: nextStage, note }, { onSuccess: () => setNote('') })}
                disabled={!canAdvance}
                title={!gatePassed ? t('promote.advance.disabledHint') : undefined}
                className="rounded-md border border-border px-3 py-1.5 hover:text-text disabled:opacity-50"
              >
                {advance.isPending ? t('promote.advance.advancing') : t('promote.advance.button', { stage: nextStageLabel })}
              </button>
              {advance.isError && (
                // A4：後端把非法轉移映成 400 BAD_REQUEST；gate-blocked advance 則映成
                // 409 IS_GATE_NOT_PASSED（backstop——前端已用 validation_status 先行 gate）。
                // 契約側的 gate-blocked 專用語意保留，並以 i18n 本地化；其餘錯誤走中央化 errText。
                <span className="text-error">
                  {advance.error instanceof ApiError && advance.error.code === 'IS_GATE_NOT_PASSED'
                    ? t('promote.advance.gateBlocked', { detail: advance.error.message })
                    : errText(advance.error)}
                </span>
              )}
            </div>
            {!gatePassed && <p className="text-xs text-warning">{t('promote.advance.gateWarning')}</p>}
          </div>
        ) : (
          <p className="text-sm text-text-muted">{t('promote.advance.finalStage')}</p>
        )}
      </section>

      {/* immutable audit */}
      <section className="rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">{t('promote.audit.title')}</h2>
          <span className="text-xs text-text-muted">{t('promote.audit.source')}</span>
        </div>
        {audit.isLoading ? (
          <SkeletonRows rows={2} cols={3} />
        ) : (audit.data?.data ?? []).length === 0 ? (
          <p className="text-sm text-text-muted">{t('promote.audit.empty')}</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {(audit.data?.data ?? []).map((ev, i) => (
              <li
                key={i}
                className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-1.5 text-sm"
              >
                <EnumBadge family="stage" value={ev.stage} />
                <span className="text-text-secondary">{ev.note || '—'}</span>
                <span className="ml-auto font-mono text-xs text-text-muted tabular">
                  {ev.actor} · {ev.at}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
