/*
 * Pending 態：端點尚未上線（doc 25 deferred / 未接線）。
 * GOAL.md 硬約束 #8：渲染 pending，絕不假造數字。
 */
import { StatusBadge } from './StatusBadge'

export function PendingNote({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-muted">
      <StatusBadge tone="muted">待後端</StatusBadge>
      <span>{label}（端點尚未接線，先不顯示數字）</span>
    </div>
  )
}
