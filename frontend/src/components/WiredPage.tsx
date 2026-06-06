/*
 * WiredPage — 端點已接線但 live 資料待 M4/needs-work 的頁面「實作」。
 * 呼叫真實主端點，四態完備：loading/error/pending(meta.data_source)/empty/data。
 * 後端 producer 一上線（meta 不再 pending、data 有值），同一頁即自動點亮 —— 無需改 code。
 * 各 section 結構抽自 design.pen frame（PAGE_SECTIONS）。
 */
import { PageHeader } from './PageHeader'
import { PendingNote } from './PendingNote'
import { Skeleton } from './Skeleton'
import { StatusBadge } from './StatusBadge'
import { useEndpoint } from '@/hooks/useEndpoint'
import { isPending } from '@/types/domain'
import { PAGE_SECTIONS } from '@/app/pageSections'

export function WiredPage({
  title,
  route,
  spec,
  endpoint,
  subtitle,
}: {
  title: string
  route: string
  spec: string
  /** 主資料端點（null = 此頁無單一 GET 主端點，如 sweep 由 POST job 驅動） */
  endpoint: string | null
  subtitle?: string
}) {
  const q = useEndpoint(endpoint)
  const sections = PAGE_SECTIONS[spec] ?? []
  const pending = isPending(q.data?.meta)
  const data = q.data?.data
  const empty = Array.isArray(data) ? data.length === 0 : data == null

  return (
    <div>
      <PageHeader title={title} route={route} subtitle={subtitle ?? '端點已接線；live 資料待 M4 producer'} />

      {/* 主資料區狀態 */}
      {endpoint && (
        <div className="mb-3">
          {q.isLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : q.isError ? (
            <div className="rounded-lg border border-border bg-surface p-4 text-sm">
              <span className="text-error">載入失敗：{(q.error as Error)?.message}</span>
              <button
                onClick={() => q.refetch()}
                className="ml-3 rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
              >
                重試
              </button>
            </div>
          ) : pending ? (
            <PendingNote label={`主端點 ${endpoint}（typed-empty，live 資料待 M4）`} />
          ) : empty ? (
            <div className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">
              {endpoint}：目前無資料
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border bg-surface p-3">
              <pre className="font-mono text-xs text-text-secondary">{JSON.stringify(data, null, 2).slice(0, 2000)}</pre>
            </div>
          )}
        </div>
      )}

      {/* design.pen section 結構 */}
      <div className="flex flex-col gap-2">
        {sections.map((s) => (
          <section key={s} className="rounded-lg border border-border bg-surface p-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-text-secondary">{s}</span>
              <StatusBadge tone="muted">{endpoint && !pending && !empty ? 'wired' : 'pending · M4'}</StatusBadge>
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
