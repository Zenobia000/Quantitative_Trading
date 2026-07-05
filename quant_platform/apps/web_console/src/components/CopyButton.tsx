/*
 * CopyButton — 一鍵複製任意文字 + 短暫「已複製」回饋。
 * 提煉自 WatchPage 的指令複製 pattern（clipboard.writeText + 1.5s 回饋切換），
 * 供資料卡 key 複製等處共用；沿用 common:action.copy / copied（雙語已存在）。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export function CopyButton({
  value,
  label,
  className = '',
}: {
  /** 要寫入剪貼簿的字串 */
  value: string
  /** 無障礙標籤（覆寫預設的 common:action.copy），如「複製 key」 */
  label?: string
  className?: string
}) {
  const { t } = useTranslation('common')
  const [copied, setCopied] = useState(false)
  const copy = () => {
    // optional chaining：jsdom / 非安全脈絡下 clipboard 可能不存在，不讓 UI 崩潰
    void navigator.clipboard?.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={label ?? t('action.copy')}
      className={`shrink-0 rounded border border-border px-2 py-0.5 text-xs text-text-muted hover:text-text ${className}`}
    >
      {copied ? t('action.copied') : t('action.copy')}
    </button>
  )
}
