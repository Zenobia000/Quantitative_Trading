/*
 * 手動建分支彈窗（Goal 9，origin=manual）—— 選一個 config 欄位 + 新值 → fork。
 * 送出鈕在欄位/值為空時 disabled；值以「數字→number、true/false→boolean、其餘→string」coerce
 * （後端再以 config_model 值域驗證，越界回 422 顯示在彈窗內、不關閉，讓使用者改值重送）。
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ConfigDeltaEntry } from '../../api/branches'

/** 使用者輸入字串 → JSON 值（number / boolean / string）。 */
export function coerceValue(raw: string): unknown {
  const s = raw.trim()
  if (s === 'true') return true
  if (s === 'false') return false
  const n = Number(s)
  return s !== '' && Number.isFinite(n) ? n : s
}

export function BranchCreateDialog({
  strategy,
  configFields,
  error,
  submitting = false,
  onSubmit,
  onCancel,
}: {
  strategy: string
  /** parent 策略 config_model 欄位名（可 fork 的 config key）。 */
  configFields: string[]
  /** mutation 失敗訊息（422 越界 / 400 …）——顯示於彈窗，不關閉。 */
  error?: string
  submitting?: boolean
  onSubmit: (delta: ConfigDeltaEntry[], note: string) => void
  onCancel: () => void
}) {
  const { t } = useTranslation('research')
  const [key, setKey] = useState(configFields[0] ?? '')
  const [value, setValue] = useState('')
  const [note, setNote] = useState('')
  const ref = useRef<HTMLSelectElement>(null)
  const valid = key.trim().length > 0 && value.trim().length > 0 && !submitting

  useEffect(() => {
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  const submit = () => {
    if (!valid) return
    onSubmit([{ key, to: coerceValue(value) }], note.trim())
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-base/70 p-4"
      role="presentation"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('branches.create.title')}
        data-testid="branch-create-dialog"
        className="w-full max-w-md rounded-lg border border-border bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold">{t('branches.create.title')}</h2>
        <p className="mt-1 text-sm text-text-secondary">{t('branches.create.subtitle', { strategy })}</p>

        <label className="mt-4 block text-xs text-text-muted">
          {t('branches.create.keyLabel')}
          <select
            ref={ref}
            data-testid="branch-create-key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            className="mt-1 w-full rounded-md border border-border bg-base px-2 py-1 font-mono text-sm text-text"
          >
            {configFields.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>

        <label className="mt-3 block text-xs text-text-muted">
          {t('branches.create.valueLabel')}
          <input
            data-testid="branch-create-value"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={t('branches.create.valuePlaceholder')}
            className="mt-1 w-full rounded-md border border-border bg-base px-2 py-1 font-mono text-sm text-text"
          />
        </label>

        <label className="mt-3 block text-xs text-text-muted">
          {t('branches.create.noteLabel')}
          <input
            data-testid="branch-create-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={t('branches.create.notePlaceholder')}
            className="mt-1 w-full rounded-md border border-border bg-base px-2 py-1 text-sm text-text"
          />
        </label>

        {error && (
          <p className="mt-3 text-xs text-error" data-testid="branch-create-error">
            {error}
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-text-secondary hover:text-text"
          >
            {t('common:action.cancel')}
          </button>
          <button
            onClick={submit}
            disabled={!valid}
            data-testid="branch-create-submit"
            className="rounded-md bg-text px-4 py-1.5 text-sm font-medium text-base hover:opacity-90 disabled:opacity-40"
          >
            {submitting ? t('branches.create.submitting') : t('branches.create.submit')}
          </button>
        </div>
      </div>
    </div>
  )
}
