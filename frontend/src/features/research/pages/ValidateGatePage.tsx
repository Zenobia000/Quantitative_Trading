/*
 * Validate gate（/research/validate?run_id=）。三源對齊 assembly + design.pen frame + page spec。
 * is_gate_checklist 接真實 GET /gate/spec（shipped，顯示硬門檻規格）。
 * 選定 candidate run（?run_id=）後：接真實 GET /research/validate/{id}/gate-state（validation_status
 * + stage + 轉移歷史）與 GET /research/validate/{id}/wfa（IS252/OOS63 rolling fold 日期窗）。
 * WFA scatter（per-fold IS/OOS 績效）需 parquet → pending；OOS vault / redline / signoff 亦 pending。
 */
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useGateSpec } from '../hooks/useGateSpec'
import { useGateState } from '../hooks/useGateState'
import { useValidateWfa } from '../hooks/useValidateWfa'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'

function statusTone(s?: string | null): 'gain' | 'loss' | 'warning' | 'muted' {
  if (!s) return 'muted'
  if (s.includes('pass')) return 'gain'
  if (s.includes('fail')) return 'loss'
  return 'warning'
}

export function ValidateGatePage() {
  const [sp, setSp] = useSearchParams()
  const runId = sp.get('run_id') ?? ''
  const [input, setInput] = useState(runId)

  const { data, isLoading, isError, error, refetch } = useGateSpec()
  const criteria = data?.data?.criteria ?? []

  const gateState = useGateState(runId || undefined)
  const wfa = useValidateWfa(runId || undefined)
  const gs = gateState.data?.data
  const folds = wfa.data?.data?.folds ?? []
  const wfaCriteria = wfa.data?.data?.criteria ?? {}

  return (
    <div>
      <PageHeader
        title="Validate gate"
        route="/research/validate"
        subtitle="不可逆 gate 狀態機 · 證明 edge 真實非過擬合"
      />

      {/* candidate run selector */}
      <section className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-3 text-sm">
        <label className="text-xs text-text-secondary">Candidate run_id</label>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="run_… （送驗證的候選 run）"
          className="min-w-[220px] flex-1 rounded-md border border-border bg-input px-3 py-1.5 font-mono text-xs"
        />
        <button
          onClick={() => setSp(input.trim() ? { run_id: input.trim() } : {})}
          className="rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
        >
          載入
        </button>
        {gs && (
          <StatusBadge tone={statusTone(gs.validation_status)}>
            {gs.validation_status ?? 'draft'} · {gs.stage ?? '—'}
          </StatusBadge>
        )}
      </section>

      {/* gate_status_header — 需 candidate run */}
      {!runId && (
        <div className="mb-3">
          <PendingNote label="Gate 狀態機（Draft→IS→WFA→OOS）+ 試驗數 / power gauge（請先輸入 candidate run_id）" />
        </div>
      )}

      {/* is_gate_checklist — 真實 GET /gate/spec */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">IS gate 硬門檻</h2>
          <span className="text-xs text-text-muted">（GET /gate/spec · 規格）</span>
        </div>
        {isLoading ? (
          <SkeletonRows rows={5} cols={3} />
        ) : isError ? (
          <div className="text-sm">
            <p className="text-error">gate 規格載入失敗：{(error as Error)?.message}</p>
            <button onClick={() => refetch()} className="mt-2 rounded-md border border-border px-3 py-1 hover:text-text">
              重試
            </button>
          </div>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {criteria.map((c) => (
              <li
                key={c.key}
                className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-1.5 text-sm"
              >
                <StatusBadge tone={c.kind === 'edge' ? 'gain' : 'muted'}>{c.kind}</StatusBadge>
                <span className="text-text">{c.label}</span>
                <span className="ml-auto font-mono text-xs text-text-secondary tabular">
                  {c.key} {c.op} {c.threshold}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* gate-state history — 真實 GET /research/validate/{id}/gate-state */}
      {runId && (
        <section className="mb-3 rounded-lg border border-border bg-surface p-4">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-[18px] font-semibold">驗證狀態轉移</h2>
            <span className="text-xs text-text-muted">（gate-state · 持久化 history）</span>
          </div>
          {gateState.isLoading ? (
            <SkeletonRows rows={2} cols={2} />
          ) : (gs?.history ?? []).length === 0 ? (
            <p className="text-sm text-text-muted">此 run 尚無驗證轉移紀錄。</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {(gs?.history ?? []).map((ev, i) => (
                <li key={i} className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-1.5 text-sm">
                  <StatusBadge tone={statusTone(ev.validation_status)}>{ev.validation_status}</StatusBadge>
                  <span className="text-text-secondary">{ev.stage}</span>
                  <span className="ml-auto font-mono text-xs text-text-muted tabular">{ev.at}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* WFA folds — 真實 GET /research/validate/{id}/wfa（folds data-free；scatter pending） */}
      {runId && (
        <section className="mb-3 rounded-lg border border-border bg-surface p-4">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-[18px] font-semibold">WFA folds</h2>
            <span className="text-xs text-text-muted">（IS 252d + OOS 63d rolling 63d）</span>
          </div>
          {wfa.isLoading ? (
            <SkeletonRows rows={3} cols={4} />
          ) : folds.length === 0 ? (
            <p className="text-sm text-text-muted">此 run 無 fold（缺 IS 區間或視窗過短）。</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-muted">
                    <th className="p-2 font-medium">#</th>
                    <th className="p-2 font-medium">IS</th>
                    <th className="p-2 font-medium">OOS</th>
                  </tr>
                </thead>
                <tbody>
                  {folds.map((f) => (
                    <tr key={f.fold} className="border-b border-border/60">
                      <td className="p-2 font-mono tabular text-text-muted">{f.fold}</td>
                      <td className="p-2 font-mono text-xs tabular">{f.is_start} ~ {f.is_end}</td>
                      <td className="p-2 font-mono text-xs tabular">{f.oos_start} ~ {f.oos_end}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {Object.keys(wfaCriteria).length > 0 && (
            <ul className="mt-3 flex flex-col gap-1 text-xs text-text-secondary">
              {Object.entries(wfaCriteria).map(([k, v]) => (
                <li key={k}>· {String(v)}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* 仍需後端／parquet 的階段 */}
      <div className="flex flex-col gap-2">
        <PendingNote label="WFA IS-vs-OOS scatter（per-fold 績效，需 parquet）" />
        <PendingNote label="OOS sealed vault（IS 過後解封）" />
        <PendingNote label="PBO / DSR 紅線（吃試驗次數 deflate）" />
        <PendingNote label="事前承諾對照 + 風控簽核（不可逆 approved）" />
      </div>
    </div>
  )
}
