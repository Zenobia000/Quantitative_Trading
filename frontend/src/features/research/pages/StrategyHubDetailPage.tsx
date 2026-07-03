/*
 * 策略中心 · 詳情（/research/strategies/:name）—— hub 的策略軸聚合視圖（深連結、refresh-safe）。
 *  - 頁首：策略名 / title / config_model 摘要（型錄 config_schema 欄位）
 *  - 觀察艙卡：在艙才顯示（複用 useWatchOverview 資料 hook）——觀察日 N/~60、到期倒數、DSR
 *  - 判決時間線：該策略的 runs 依帳本序（gate badge + 關鍵 metrics + 連 RunReport）
 *  - 快速入口：New Run（帶 strategy 預填）、K 線覆盤、Compare、最近 run 的 Open-in-notebook
 * 資料聚合全用既有端點（/strategies + /runs + /monitor/watch），不需新後端。
 */
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useStrategyHubDetail } from '../hooks/useStrategyHub'
import type { WatchRow } from '@/features/monitor/hooks/useWatch'
import { PageHeader } from '@/components/PageHeader'
import { Skeleton, SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { useErrorText } from '@/i18n/useErrorText'

function fmtMetric(v: unknown): string {
  return typeof v === 'number' ? (Number.isInteger(v) ? String(v) : v.toFixed(2)) : '—'
}

function fmtPct(v: unknown): string {
  return typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '—'
}

/** 由 JSON-schema 的 config_schema 抽出參數欄位名（config_model 摘要）。 */
function configFields(schema: Record<string, unknown> | undefined): string[] {
  const props = (schema as { properties?: unknown } | undefined)?.properties
  return props && typeof props === 'object' ? Object.keys(props as object) : []
}

export function StrategyHubDetailPage() {
  const { t } = useTranslation(['research', 'monitor'])
  const errText = useErrorText()
  const navigate = useNavigate()
  const { name } = useParams<{ name: string }>()
  const { registry, runsQ, detail } = useStrategyHubDetail(name)

  const back = { label: t('strategyHub.detail.back'), to: '/research/strategies' }
  const route = `/research/strategies/${encodeURIComponent(name ?? '')}`
  const fields = configFields(detail.info?.config_schema)
  // Open-in-notebook：直連後端下載端點（VITE_API_BASE 對齊 http client；dev 走相對路徑 proxy）。
  const notebookHref = detail.latestRun
    ? `${import.meta.env.VITE_API_BASE ?? ''}/runs/${encodeURIComponent(detail.latestRun.run_id)}/notebook`
    : null

  // 主 loading：型錄 + runs 皆載入中 → 骨架（任一到位即開始漸進呈現）。
  if (registry.isLoading && runsQ.isLoading) {
    return (
      <div>
        <PageHeader title={detail.title} route={route} back={back} />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title={detail.title} route={route} subtitle={detail.info?.description} back={back} />

      {/* config_model 摘要 / 型錄外策略提示 */}
      {detail.info ? (
        fields.length > 0 && (
          <div className="mb-3 rounded-lg border border-border bg-surface p-3">
            <div className="mb-1 text-xs text-text-muted">{t('strategyHub.detail.configFields')}</div>
            <div className="flex flex-wrap gap-1.5">
              {fields.map((f) => (
                <span
                  key={f}
                  className="rounded-md border border-border bg-surface-raised px-2 py-0.5 font-mono text-xs text-text-secondary"
                >
                  {f}
                </span>
              ))}
            </div>
          </div>
        )
      ) : (
        <div className="mb-3 rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-xs text-text-muted">
          {t('strategyHub.detail.notInRegistry', { name: detail.name })}
        </div>
      )}

      {/* 觀察艙卡（在艙才顯示） */}
      {detail.watch && <WatchPodCard row={detail.watch} />}

      {/* 快速入口列 */}
      <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm">
        <button
          onClick={() => navigate(`/research/runs/new?strategy=${encodeURIComponent(detail.name)}`)}
          className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
        >
          {t('strategyHub.detail.actions.newRun')}
        </button>
        <button
          onClick={() => detail.latestRun && navigate(`/research/runs/${encodeURIComponent(detail.latestRun.run_id)}/trades`)}
          disabled={!detail.latestRun}
          title={!detail.latestRun ? t('strategyHub.detail.actions.needRun') : undefined}
          className="rounded-md border border-border px-3 py-1 text-text-secondary enabled:hover:text-text disabled:opacity-40"
        >
          {t('strategyHub.detail.actions.tradeReview')}
        </button>
        <button
          onClick={() =>
            navigate(`/research/compare?run_ids=${detail.runs.map((r) => encodeURIComponent(r.run_id)).join(',')}`)
          }
          disabled={detail.runs.length < 2}
          title={detail.runs.length < 2 ? t('strategyHub.detail.actions.needTwo') : undefined}
          className="rounded-md border border-border px-3 py-1 text-text-secondary enabled:hover:text-text disabled:opacity-40"
        >
          {t('strategyHub.detail.actions.compare')}
        </button>
        {notebookHref && (
          <a
            href={notebookHref}
            target="_blank"
            rel="noreferrer"
            className="ml-auto rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
          >
            {t('strategyHub.detail.actions.notebook')}
          </a>
        )}
      </div>

      {/* 判決時間線 */}
      <section className="rounded-lg border border-border bg-surface">
        <div className="border-b border-border px-4 py-2 text-xs uppercase tracking-wide text-text-muted">
          {t('strategyHub.detail.timeline.title')}
        </div>
        {runsQ.isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={4} cols={3} />
          </div>
        ) : runsQ.isError ? (
          <div className="p-6 text-sm">
            <p className="text-error">
              {t('errors:load.failed', { resource: t('strategyHub.detail.resource'), detail: errText(runsQ.error) })}
            </p>
            <button
              onClick={() => runsQ.refetch()}
              className="mt-3 rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
            >
              {t('common:action.retry')}
            </button>
          </div>
        ) : detail.runs.length === 0 ? (
          <div className="p-6 text-sm text-text-muted">{t('strategyHub.detail.timeline.empty')}</div>
        ) : (
          <ol className="divide-y divide-border/60">
            {detail.runs.map((r) => (
              <li key={r.run_id}>
                <button
                  onClick={() => navigate(`/research/runs/${encodeURIComponent(r.run_id)}`)}
                  className="flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left hover:bg-input"
                >
                  <EnumBadge family="gate" value={r.gate_status} />
                  <span className="font-mono text-xs tabular text-text">{r.run_id}</span>
                  <span className="flex gap-3 font-mono text-xs tabular text-text-secondary">
                    <span>Sharpe {fmtMetric(r.metrics?.sharpe)}</span>
                    <span>CAGR {fmtPct(r.metrics?.cagr)}</span>
                    <span>MaxDD {fmtPct(r.metrics?.maxdd)}</span>
                  </span>
                  {r.hypothesis && (
                    <span className="ml-auto max-w-[240px] truncate text-xs text-text-muted" title={r.hypothesis}>
                      {r.hypothesis}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}

/** 觀察艙卡（compact）—— 複用 useWatchOverview 的 WatchRow；沿用 WatchPage 的進度 / 到期呈現。 */
function WatchPodCard({ row }: { row: WatchRow }) {
  const { t } = useTranslation(['research', 'monitor'])
  const pct =
    row.nominal_trading_days > 0
      ? Math.min(100, Math.round((row.observed_trading_days / row.nominal_trading_days) * 100))
      : 0
  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-text-muted">{t('research:strategyHub.detail.watch.title')}</span>
        <EnumBadge family="watchState" value={row.status} />
        <span className="ml-auto font-mono text-xs tabular text-text-muted">DSR {row.verdict_dsr.toFixed(4)}</span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <div className="mb-1 flex items-baseline justify-between text-xs text-text-muted">
            <span>{t('monitor:watch.observedDays')}</span>
            <span className="font-mono tabular text-text-secondary">
              {row.observed_trading_days}/~{row.nominal_trading_days}
            </span>
          </div>
          <div
            className="h-2 w-full overflow-hidden rounded-full bg-surface-raised"
            role="progressbar"
            aria-valuenow={pct}
          >
            <div className="h-full rounded-full bg-gain/70" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="flex flex-col justify-center text-sm">
          <div className="text-xs text-text-muted">{t('monitor:watch.expiry', { date: row.expiry_date })}</div>
          <div className="font-mono tabular text-text-secondary">
            {row.days_remaining >= 0
              ? t('monitor:watch.daysRemaining', { days: row.days_remaining })
              : t('monitor:watch.overdue', { days: -row.days_remaining })}
          </div>
        </div>
      </div>
    </section>
  )
}
