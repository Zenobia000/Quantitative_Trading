/*
 * ReasonDialog —— override / archive 必填理由的攔截彈窗（契約 §6.3 override 規則）。
 * 送出鈕在理由為空白時 disabled（前端強制），送出回傳 trim 後理由。
 * 非 eligible 的 Live-OOS 勾選會顯示 override 說明（當前 recommendation）。
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { CandidateAction } from './candidateDisplay'

export function ReasonDialog({
  action,
  strategy,
  recommendationLabel,
  error,
  submitting = false,
  onSubmit,
  onCancel,
}: {
  action: CandidateAction
  strategy: string
  /** 非 eligible 勾選時顯示的建議標籤（override 情境）；archive 時可省略。 */
  recommendationLabel?: string
  /** api 模式 mutation 失敗訊息（400/409/422）——顯示在彈窗內，彈窗不關閉，讓使用者改理由重送。 */
  error?: string
  /** mutation 進行中：禁用送出 + 顯示送出中，避免重複提交。 */
  submitting?: boolean
  onSubmit: (reason: string) => void
  onCancel: () => void
}) {
  const { t } = useTranslation('research')
  const [reason, setReason] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)
  const valid = reason.trim().length > 0 && !submitting

  useEffect(() => {
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-base/70 p-4"
      role="presentation"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('candidates.reason.title')}
        className="w-full max-w-md rounded-lg border border-border bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold">{t('candidates.reason.title')}</h2>
        <p className="mt-1 text-sm text-text-secondary">
          {t(`candidates.reason.${action}`, { strategy })}
        </p>
        {recommendationLabel && (
          <p className="mt-2 rounded-md border border-warning/40 bg-surface px-3 py-2 text-xs text-warning">
            {t('candidates.reason.override', { reco: recommendationLabel })}
          </p>
        )}
        <label className="mt-3 block text-xs text-text-muted" htmlFor="candidate-reason">
          {t('candidates.reason.label')}
        </label>
        <textarea
          id="candidate-reason"
          ref={ref}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          placeholder={t('candidates.reason.placeholder')}
          className="mt-1 w-full resize-none rounded-md border border-border bg-input px-3 py-2 text-sm text-text placeholder:text-text-muted focus:border-text/40 focus:outline-none"
        />
        {reason.trim().length === 0 && (
          <p className="mt-1 text-[11px] text-text-muted">{t('candidates.reason.required')}</p>
        )}
        {error && (
          <p
            role="alert"
            className="mt-3 rounded-md border border-error/50 bg-surface px-3 py-2 text-xs text-error"
          >
            {t('candidates.reason.submitError', { detail: error })}
          </p>
        )}
        <div className="mt-4 flex items-center justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-text-secondary hover:text-text"
          >
            {t('candidates.reason.cancel')}
          </button>
          <button
            onClick={() => valid && onSubmit(reason.trim())}
            disabled={!valid}
            className="rounded-pill bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90 disabled:opacity-40"
          >
            {submitting ? t('candidates.reason.submitting') : t('candidates.reason.submit')}
          </button>
        </div>
      </div>
    </div>
  )
}
