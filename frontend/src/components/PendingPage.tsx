/*
 * PendingPage — 端點未接線頁的忠實殼：依 design.pen frame 的 section 結構逐區呈現 pending 態。
 * GOAL.md 硬約束 #8：渲染 pending，不假造資料。端點 ship 後逐區換成實作。
 */
import { PageHeader } from './PageHeader'
import { StatusBadge } from './StatusBadge'
import { PAGE_SECTIONS } from '@/app/pageSections'

export function PendingPage({ title, route, spec }: { title: string; route: string; spec: string }) {
  const sections = PAGE_SECTIONS[spec] ?? []
  return (
    <div>
      <PageHeader title={title} route={route} subtitle="後端端點尚未接線——以下為頁面 section 結構（pending）" />
      <div className="flex flex-col gap-2">
        {sections.length === 0 && (
          <div className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">
            （此頁 section 結構待補）
          </div>
        )}
        {sections.map((s) => (
          <section key={s} className="rounded-lg border border-border bg-surface p-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-text-secondary">{s}</span>
              <StatusBadge tone="muted">待後端</StatusBadge>
            </div>
          </section>
        ))}
      </div>
      <p className="mt-3 text-xs text-text-muted">
        建頁參照：<span className="font-mono">pages/{spec}.md</span> ·{' '}
        <span className="font-mono">assembly/{spec}_integrated.md</span> · design.pen「{title}」frame
      </p>
    </div>
  )
}
