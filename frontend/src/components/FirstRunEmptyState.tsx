/*
 * FirstRunEmptyState — 零資料引導（對齊 design.pen Section · empty_state）。
 * 置中大圓角卡 + 1px border 無陰影 + 可複製真實 CLI + 單一白 pill CTA + three-path。
 */
import { useState } from 'react'

const DEFAULT_CLI = 'backtest-run --stocks 2330,2454 --start 2020-01-01 --end 2024-12-31'

export function FirstRunEmptyState({
  headline = '尚無策略，從第一次回測開始',
  subtitle = '貼上一行 CLI 或點下方按鈕，開始你的第一個策略迭代',
  cli = DEFAULT_CLI,
  ctaLabel = '建立第一個策略',
  onCta,
}: {
  headline?: string
  subtitle?: string
  cli?: string
  ctaLabel?: string
  onCta?: () => void
}) {
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
      <h2 className="text-[22px] font-semibold">{headline}</h2>
      <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>
      <button
        onClick={copy}
        className="mt-5 block w-full truncate rounded-md border border-border bg-code px-4 py-3 text-left font-mono text-xs text-text-secondary hover:text-text"
        title="點擊複製"
      >
        $ {cli}
        <span className="ml-2 text-text-muted">{copied ? '✓ 已複製' : '⧉'}</span>
      </button>
      <button
        onClick={onCta}
        className="mt-5 rounded-pill bg-text px-5 py-2 text-sm font-medium text-base hover:opacity-90"
      >
        {ctaLabel}
      </button>
      <div className="mt-4 text-xs text-text-muted">
        跑範例策略 · 看文件 · 貼 CLI
      </div>
    </div>
  )
}
