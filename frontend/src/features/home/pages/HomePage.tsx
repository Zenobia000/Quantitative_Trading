/*
 * 首頁 · 控制塔（/）。三源對齊 assembly + design.pen frame + page spec。
 * research_status + recent_activity 接真實 /home/*（read_runs 聚合）；
 * fleet_strip + system_health 需 live 資料（M4）→ pending（不假造數字）。
 */
import { useNavigate } from 'react-router-dom'
import { useRecent, useResearchStatus } from '../hooks/useHome'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { Skeleton } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'

function Kpi({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="text-xs text-text-muted">{label}</div>
      <div className="mt-1 font-mono text-lg tabular">{value}</div>
    </div>
  )
}

export function HomePage() {
  const navigate = useNavigate()
  const rs = useResearchStatus()
  const rec = useRecent()
  const status = rs.data?.data
  const recent = rec.data?.data ?? []
  const isNewPlatform = status?.total_runs === 0 && !rs.isLoading

  return (
    <div>
      <PageHeader title="首頁 · 控制塔" route="/" subtitle="跨三區總覽——研究迴圈 / 艦隊健康 / 系統狀態" />

      {/* command_hero */}
      <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3">
        <button className="rounded-pill border border-border px-3 py-1 text-xs text-text-muted">⌘K 搜尋 / 跳轉</button>
        <button
          onClick={() => navigate('/research/runs/new')}
          className="ml-auto rounded-pill bg-text px-4 py-1 text-sm font-medium text-base hover:opacity-90"
        >
          New Run
        </button>
        <button
          onClick={() => navigate('/research/runs')}
          className="rounded-md border border-border px-3 py-1 text-sm text-text-secondary hover:text-text"
        >
          Runs
        </button>
        <button
          onClick={() => navigate('/monitor')}
          className="rounded-md border border-border px-3 py-1 text-sm text-text-secondary hover:text-text"
        >
          艦隊
        </button>
      </div>

      {isNewPlatform ? (
        <FirstRunEmptyState
          headline="歡迎——從第一個策略開始"
          onCta={() => navigate('/research/runs/new')}
        />
      ) : (
        <>
          {/* fleet_strip — live 資料 M4 */}
          <div className="mb-3">
            <PendingNote label="策略艦隊（live/paper 健康 + 今日績效 + 退化示警）" />
          </div>

          {/* research_status — 真接 */}
          <section className="mb-3">
            <h2 className="mb-2 text-sm text-text-secondary">研究狀態</h2>
            {rs.isLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : rs.isError ? (
              <div className="rounded-lg border border-border bg-surface p-4 text-sm text-error">
                研究狀態載入失敗：{(rs.error as Error)?.message}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Kpi label="總 run 數" value={status?.total_runs ?? '—'} />
                <Kpi
                  label="最新 gate"
                  value={
                    status?.latest_gate_status ? (
                      <StatusBadge tone={status.latest_gate_status === 'PASS' ? 'gain' : 'loss'}>
                        {status.latest_gate_status}
                      </StatusBadge>
                    ) : (
                      '—'
                    )
                  }
                />
                <Kpi label="試驗數" value={status?.trials ?? '待後端'} />
                <Kpi label="DSR" value={status?.dsr ?? '待後端'} />
              </div>
            )}
          </section>

          {/* system_health — live 資料 M4 */}
          <div className="mb-3">
            <PendingNote label="系統健康（bundle 新鮮度 / 告警計數 / FinLab quota）" />
          </div>

          {/* recent_activity — 真接 */}
          <section>
            <h2 className="mb-2 text-sm text-text-secondary">最近活動</h2>
            {rec.isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : recent.length === 0 ? (
              <div className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">尚無近期活動</div>
            ) : (
              <ul className="flex flex-col gap-1">
                {recent.map((r, i) => (
                  <li
                    key={i}
                    onClick={() => r.run_id && navigate(`/research/runs/${encodeURIComponent(r.run_id)}`)}
                    className="flex cursor-pointer items-center gap-3 rounded-md border border-border/60 bg-surface px-3 py-1.5 text-sm hover:bg-input"
                  >
                    <StatusBadge tone="muted">{r.type}</StatusBadge>
                    <span className="font-mono text-xs tabular">{r.run_id}</span>
                    <span className="text-text-secondary">{r.preset}</span>
                    {r.gate_status && <span className="ml-auto text-xs text-text-muted">{r.gate_status}</span>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  )
}
