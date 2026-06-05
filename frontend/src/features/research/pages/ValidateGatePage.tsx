/*
 * Validate gate（/research/validate）。三源對齊 assembly + design.pen frame + page spec。
 * is_gate_checklist 接真實 GET /gate/spec（shipped，顯示硬門檻規格）；
 * gate_status / OOS vault / WFA / redline / signoff 需 candidate run 評估端點（/gate/evaluate POST，
 * 但需先選 candidate）→ 先呈現規格 + pending（不假造數字）。
 */
import { useGateSpec } from '../hooks/useGateSpec'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'

export function ValidateGatePage() {
  const { data, isLoading, isError, error, refetch } = useGateSpec()
  const criteria = data?.data?.criteria ?? []

  return (
    <div>
      <PageHeader
        title="Validate gate"
        route="/research/validate"
        subtitle="不可逆 gate 狀態機 · 證明 edge 真實非過擬合"
      />

      {/* gate_status_header — 需 candidate run，先 pending */}
      <div className="mb-3">
        <PendingNote label="Gate 狀態機（Draft→IS→WFA→OOS）+ 試驗數 / power gauge（需選定 candidate run）" />
      </div>

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

      {/* 其餘 gate 階段需 candidate run 評估 */}
      <div className="flex flex-col gap-2">
        <PendingNote label="OOS sealed vault（IS 過後解封；需 candidate run）" />
        <PendingNote label="WFA fold 一致性 + IS-vs-OOS scatter" />
        <PendingNote label="PBO / DSR 紅線（吃試驗次數 deflate）" />
        <PendingNote label="事前承諾對照 + 風控簽核（不可逆 approved）" />
      </div>
    </div>
  )
}
