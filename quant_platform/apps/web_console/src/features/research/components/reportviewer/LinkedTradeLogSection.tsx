/*
 * Linked trade log —— 契約有 run（run_id）就連結到 /research/runs/:id/trades（既有逐筆覆盤頁）。
 * panel 策略的 trades 只有再平衡列、無 per-trade pnl → Win-Rate/Liquidity 交易指標維持 not_available，
 * 這裡以 caveat 誠實揭露 partial。無 run_id → not_available。
 */
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { StatusBadge } from '@/components/StatusBadge'

export function LinkedTradeLogSection({ runId, partial }: { runId: string | null; partial: boolean }) {
  const { t } = useTranslation('research')
  const navigate = useNavigate()

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <h2 className="mb-2 text-[18px] font-semibold">{t('reportViewer.trades.title')}</h2>
      {runId ? (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/research/runs/${encodeURIComponent(runId)}/trades`)}
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-text-secondary hover:text-text"
          >
            <span aria-hidden>→</span>
            {t('reportViewer.trades.link')}
          </button>
          {partial && (
            <StatusBadge tone="warning">
              <span aria-hidden>△</span>
              {t('reportViewer.trades.partial')}
            </StatusBadge>
          )}
        </div>
      ) : (
        <p className="rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-sm text-text-muted">
          {t('reportViewer.trades.notAvailable')}
        </p>
      )}
      {partial && runId && (
        <p className="mt-2 text-xs text-text-muted">{t('reportViewer.trades.partialNote')}</p>
      )}
    </section>
  )
}
