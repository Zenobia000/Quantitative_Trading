/*
 * WiredPage — 端點已接線但 live 資料待後端 producer 的頁面「實作」。
 * 呼叫真實主端點，四態完備：loading/error/pending(meta.data_source)/empty/data。
 * 後端 producer 一上線（meta 不再 pending、data 有值），同一頁即自動點亮 —— 無需改 code。
 * 各 section 結構來自 product_repositioning/frontend IA 的 transitional PAGE_SECTIONS；
 * section id 經 sections namespace 映射為人類標籤。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from './PageHeader'
import { PendingNote } from './PendingNote'
import { Skeleton } from './Skeleton'
import { StatusBadge } from './StatusBadge'
import { useEndpoint } from '@/hooks/useEndpoint'
import { useErrorText } from '@/i18n/useErrorText'
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
  const { t } = useTranslation(['common', 'sections', 'errors'])
  const errText = useErrorText()
  const q = useEndpoint(endpoint)
  const sections = PAGE_SECTIONS[spec] ?? []
  const pending = isPending(q.data?.meta)
  const data = q.data?.data
  const empty = Array.isArray(data) ? data.length === 0 : data == null

  return (
    <div>
      <PageHeader title={title} route={route} subtitle={subtitle ?? t('common:wired.subtitle')} />

      {/* 主資料區狀態 */}
      {endpoint && (
        <div className="mb-3">
          {q.isLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : q.isError ? (
            <div className="rounded-lg border border-border bg-surface p-4 text-sm">
              <span className="text-error">{t('errors:load.failed', { resource: title, detail: errText(q.error) })}</span>
              <button
                onClick={() => q.refetch()}
                className="ml-3 rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
              >
                {t('common:action.retry')}
              </button>
            </div>
          ) : pending ? (
            <PendingNote label={t('common:wired.mainPending', { endpoint })} />
          ) : empty ? (
            <div className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">
              {t('common:wired.empty', { endpoint })}
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border bg-surface p-3">
              <pre className="font-mono text-xs text-text-secondary">{JSON.stringify(data, null, 2).slice(0, 2000)}</pre>
            </div>
          )}
        </div>
      )}

      {/* transitional page section skeleton */}
      <div className="flex flex-col gap-2">
        {sections.map((s) => (
          <section key={s} className="rounded-lg border border-border bg-surface p-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">{t(`sections:${s}`, { defaultValue: s })}</span>
              <StatusBadge tone="muted">
                {endpoint && !pending && !empty ? t('common:wired.wired') : t('common:wired.pending')}
              </StatusBadge>
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
