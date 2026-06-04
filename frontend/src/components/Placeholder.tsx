/*
 * Phase 0 佔位頁：證明路由/殼/token 可跑。Phase 2 會依
 * dev_docs/web_design/assembly/<spec>_integrated.md + pages/<spec>.md + design.pen 逐頁替換。
 */
import { StatusBadge } from './StatusBadge'

export function Placeholder({ title, route, spec }: { title: string; route: string; spec: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <div className="mb-2 flex items-center gap-3">
        <h1 className="text-[22px] font-semibold">{title}</h1>
        <StatusBadge tone="warning">Phase 2 待建</StatusBadge>
      </div>
      <p className="font-mono text-sm text-text-secondary tabular">{route}</p>
      <p className="mt-4 text-sm text-text-muted">
        建頁參照：<span className="font-mono">pages/{spec}.md</span> ·{' '}
        <span className="font-mono">assembly/{spec}_integrated.md</span> · design.pen
      </p>
    </div>
  )
}
