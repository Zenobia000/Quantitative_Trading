/*
 * Promote（/research/promote/:strategyId）— 不可逆晉升狀態機（後端 8.H.7 / S3）。
 * 接真實 GET /research/promote/{id}（current stage + gates）、POST（前進一階，draft→paper→live）、
 * GET /audit（immutable trail）。stepper 顯示已達階段，advance 鈕觸發 mutation。
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { usePromoteAudit, usePromoteState, useAdvancePromote } from '../hooks/usePromote'
import { PageHeader } from '@/components/PageHeader'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'

const STAGES = ['draft', 'paper', 'live'] as const

export function PromotePage() {
  const { strategyId } = useParams<{ strategyId: string }>()
  const sid = strategyId ?? ''
  const state = usePromoteState(sid)
  const audit = usePromoteAudit(sid)
  const advance = useAdvancePromote(sid)
  const [note, setNote] = useState('')

  const stage = state.data?.data?.stage ?? 'draft'
  const gates = state.data?.data?.gates ?? STAGES.map((s, i) => ({ stage: s, reached: i === 0 }))
  const curIdx = STAGES.indexOf(stage as (typeof STAGES)[number])
  const nextStage = curIdx >= 0 && curIdx < STAGES.length - 1 ? STAGES[curIdx + 1] : null

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
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="晉升理由（記入 audit）"
              className="min-w-[240px] flex-1 rounded-md border border-border bg-surface-raised px-3 py-1.5"
            />
            <button
              onClick={() => advance.mutate({ to_stage: nextStage, note }, { onSuccess: () => setNote('') })}
              disabled={advance.isPending}
              className="rounded-md border border-border px-3 py-1.5 hover:text-text disabled:opacity-50"
            >
              {advance.isPending ? '晉升中…' : `晉升至 ${nextStage} →`}
            </button>
            {advance.isError && <span className="text-error">{(advance.error as Error)?.message}</span>}
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
