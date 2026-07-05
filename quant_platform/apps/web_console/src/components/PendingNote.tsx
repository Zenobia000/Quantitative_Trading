/*
 * Pending 態：端點尚未上線（doc 25 deferred / 未接線）。
 * GOAL.md 硬約束 #8：渲染 pending，絕不假造數字。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from './StatusBadge'

export function PendingNote({ label }: { label: string }) {
  const { t } = useTranslation('common')
  // 虛線 + 退到 bg-base：視覺上讀作「未接線的鷹架」而非「壞掉的成品卡」，
  // 讓已完成的區塊不因並排的 pending 而看起來未完工（VH-06 / ONB-03）。
  return (
    <div className="flex items-center gap-2 border border-dashed border-border/70 bg-base px-3 py-2 text-sm text-text-muted">
      <StatusBadge tone="muted">{t('state.awaitingBackend')}</StatusBadge>
      <span>
        {label}
        {t('pending.note')}
      </span>
    </div>
  )
}
