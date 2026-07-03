/*
 * Promote（/research/promote/:strategyId）— 不可逆晉升狀態機（後端 8.H.7 / S3）。
 * 接真實 GET /research/promote/{id}（current stage + gates）、POST（前進一階，draft→paper→live）、
 * GET /audit（immutable trail）。stepper 顯示已達階段，advance 鈕觸發 mutation。
 * 前端防線（此工作包）：無 gate PASS 證據時 disable advance —— gate 證據取自 strategy roster
 * （GET /research/strategies）的 validation_status（由各 run 的 gate_status 投影）。後端硬防線屬另一工作包。
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { usePromoteAudit, usePromoteState, useAdvancePromote } from '../hooks/usePromote'
import { useStrategies } from '../hooks/useStrategies'
import { PageHeader } from '@/components/PageHeader'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { ApiError } from '@/services/http'

const STAGES = ['draft', 'paper', 'live'] as const

export function PromotePage() {
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

  // gate PASS 前置：策略須有 IS PASS 的 run（roster validation_status==='is_pass'）方可晉升。
  const rosterRows = roster.data?.data
  const strategyRow = Array.isArray(rosterRows) ? rosterRows.find((r) => r.strategy_id === sid) : undefined
  const gatePassed = strategyRow?.validation_status === 'is_pass'
  const canAdvance = !advance.isPending && gatePassed

  return (
    <div>
      <PageHeader
        title="Promotion stepper"
        route={`/research/promote/${sid}`}
        subtitle="不可逆晉升狀態機（draft→paper→live）· 每步進 immutable audit"
      />

      {/* stepper */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">{sid || '—'}</h2>
          <StatusBadge tone={stage === 'live' ? 'gain' : 'muted'}>{stage}</StatusBadge>
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
                  {g.stage}
                </span>
                {i < gates.length - 1 && <span className="text-text-muted">→</span>}
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* advance control */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-2 text-[18px] font-semibold">晉升</h2>
        {nextStage ? (
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="晉升理由（記入 audit）"
                className="min-w-[240px] flex-1 rounded-md border border-border bg-surface-raised px-3 py-1.5"
              />
              <button
                onClick={() => advance.mutate({ to_stage: nextStage, note }, { onSuccess: () => setNote('') })}
                disabled={!canAdvance}
                title={!gatePassed ? '需 gate PASS 證據方可晉升' : undefined}
                className="rounded-md border border-border px-3 py-1.5 hover:text-text disabled:opacity-50"
              >
                {advance.isPending ? '晉升中…' : `晉升至 ${nextStage} →`}
              </button>
              {advance.isError && (
                // A4：後端把非法轉移映成 400 BAD_REQUEST；gate-blocked advance 則映成
                // 409 IS_GATE_NOT_PASSED（backstop——前端已用 validation_status 先行 gate）。
                <span className="text-error">
                  {advance.error instanceof ApiError && advance.error.code === 'IS_GATE_NOT_PASSED'
                    ? `晉升被驗證閘阻擋：${advance.error.message}`
                    : (advance.error as Error)?.message}
                </span>
              )}
            </div>
            {!gatePassed && (
              <p className="text-xs text-warning">
                此策略尚無 IS gate PASS 的 run，暫不可晉升（前端防線；晉升前須先通過驗證閘）。
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-text-muted">已達最終階段（live），無可晉升。</p>
        )}
      </section>

      {/* immutable audit */}
      <section className="rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">晉升軌跡</h2>
          <span className="text-xs text-text-muted">（immutable audit · append-only）</span>
        </div>
        {audit.isLoading ? (
          <SkeletonRows rows={2} cols={3} />
        ) : (audit.data?.data ?? []).length === 0 ? (
          <p className="text-sm text-text-muted">尚無晉升紀錄。</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {(audit.data?.data ?? []).map((ev, i) => (
              <li
                key={i}
                className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-1.5 text-sm"
              >
                <StatusBadge tone="muted">{ev.stage}</StatusBadge>
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
