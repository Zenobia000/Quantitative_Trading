/*
 * FirstRunEmptyState — 零資料引導（對齊 design.pen Section · empty_state）。
 * 置中大圓角卡 + 1px border 無陰影 + 可複製真實 CLI + 單一白 pill CTA + three-path。
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const DEFAULT_CLI = 'backtest-run --stocks 2330,2454 --start 2020-01-01 --end 2024-12-31'

export function FirstRunEmptyState({
  headline,
  subtitle,
  cli = DEFAULT_CLI,
  ctaLabel,
  onCta,
  onDocs,
}: {
  headline?: string
  subtitle?: string
  cli?: string
  ctaLabel?: string
  onCta?: () => void
  /** 「看文件」on-ramp；不給則不顯示該項 */
  onDocs?: () => void
}) {
  const { t } = useTranslation('common')
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(cli)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard 不可用時忽略 */
    }
  }
  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-border bg-surface p-8 text-center">
      <h2 className="text-[22px] font-semibold">{headline ?? t('emptyState.headline')}</h2>
      <p className="mt-1 text-sm text-text-secondary">{subtitle ?? t('emptyState.subtitle')}</p>
      <button
        onClick={copy}
        className="mt-5 block w-full truncate rounded-md border border-border bg-code px-4 py-3 text-left font-mono text-xs text-text-secondary hover:text-text"
        title={t('emptyState.clickToCopy')}
      >
        $ {cli}
        <span className="ml-2 text-text-muted">{copied ? `✓ ${t('emptyState.copied')}` : '⧉'}</span>
      </button>
      <button
        onClick={onCta}
        className="mt-5 rounded-pill bg-text px-5 py-2 text-sm font-medium text-base hover:opacity-90"
      >
        {ctaLabel ?? t('emptyState.cta')}
      </button>
      {/* three-path on-ramps —— 皆為真實可點動作（非死文字） */}
      <div className="mt-4 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs">
        <button onClick={onCta} className="text-text-secondary underline-offset-2 hover:text-text hover:underline">
          {t('emptyState.runExample')}
        </button>
        <span className="text-text-muted" aria-hidden>·</span>
        <button onClick={copy} className="text-text-secondary underline-offset-2 hover:text-text hover:underline">
          {copied ? `✓ ${t('emptyState.copiedCli')}` : t('emptyState.copyCli')}
        </button>
        {onDocs && (
          <>
            <span className="text-text-muted" aria-hidden>·</span>
            <button onClick={onDocs} className="text-text-secondary underline-offset-2 hover:text-text hover:underline">
              {t('emptyState.docs')}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
