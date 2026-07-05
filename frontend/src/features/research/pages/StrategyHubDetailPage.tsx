/*
 * 策略資產 · 詳情（/research/strategies/:name）—— 單策略研究資產聚合視圖（深連結、refresh-safe，Goal 7）。
 *  - 頁首：策略名 / title
 *  - 研究命題：假設（候選 → 最近 run fallback）+ 機制（型錄 description）
 *  - config_model 摘要：型錄 config_schema 欄位（authoring 資訊）
 *  - 候選生命週期（IA 裁決 B 落地）：候選 state + 最新評測（profile / label / 五維燈 / next_action）
 *    + 決策軌跡（折疊）+ 連 Report Viewer /research/reports/:runId 與候選池；無候選 → 「尚未評估」引導
 *  - 觀察艙卡：在艙才顯示（複用 useWatchOverview 資料 hook）
 *  - 快速入口：Evaluate（主要動作，預填此策略）、K 線覆盤、Compare、Open-in-notebook
 *  - 判決時間線：該策略的 runs（gate badge + 關鍵 metrics + 連 RunReport）——降為次要證據
 * 資料聚合全用既有端點（/strategies + /runs + /monitor/watch + /research/candidates），不需新後端。
 */
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { UseQueryResult } from '@tanstack/react-query'
import { useStrategyHubDetail } from '../hooks/useStrategyHub'
import { useDatasets } from '@/features/system/hooks/useSystem'
import { BranchExperimentsSection } from '../components/branches/BranchExperimentsSection'
import { CandidateStateBadge } from '../components/candidates/CandidateStateBadge'
import { ScorecardLights } from '../components/candidates/ScorecardLights'
import { runIdFromReportRef } from '../components/candidates/candidateDisplay'
import type { Candidate } from '../api/candidates'
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

/** Evaluate 入口：evaluate 後端目前僅 CLI，前端先導既有 New Run 表單（IA §2：runs/new 併入 evaluate）。 */
function evaluateHref(name: string): string {
  return `/research/runs/new?strategy=${encodeURIComponent(name)}`
}

export function StrategyHubDetailPage() {
  const { t } = useTranslation(['research', 'monitor'])
  const errText = useErrorText()
  const navigate = useNavigate()
  const { name } = useParams<{ name: string }>()
  const { registry, runsQ, candidatesQ, detail } = useStrategyHubDetail(name)

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
      <PageHeader title={detail.title} route={route} back={back} />

      {/* 研究命題：假設 + 機制 */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 text-xs uppercase tracking-wide text-text-muted">
          {t('strategyHub.detail.premise.title')}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <div className="mb-0.5 text-[11px] text-text-muted">{t('strategyHub.detail.premise.hypothesis')}</div>
            <p className="text-sm text-text-secondary">
              {detail.hypothesis ?? (
                <span className="italic text-text-muted">{t('strategyHub.detail.premise.noHypothesis')}</span>
              )}
            </p>
          </div>
          <div>
            <div className="mb-0.5 text-[11px] text-text-muted">{t('strategyHub.detail.premise.mechanism')}</div>
            <p className="text-sm text-text-secondary">
              {detail.mechanism ?? (
                <span className="italic text-text-muted">{t('strategyHub.detail.premise.noMechanism')}</span>
              )}
            </p>
          </div>
        </div>
      </section>

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

      {/* 使用的資料卡（反向索引搬家自資料字典：語意屬策略側，多策略也不擠字典） */}
      <UsedDatasetsSection strategy={detail.name} />

      {/* 候選生命週期（IA 裁決 B） */}
      <CandidateLifecycle
        candidate={detail.candidate}
        query={candidatesQ}
        onEvaluate={() => navigate(evaluateHref(detail.name))}
      />

      {/* 分支實驗 section（Goal 9）—— 從候選最新評測 fork；config delta / evaluate / compare */}
      <BranchExperimentsSection
        strategy={detail.name}
        parentEvaluationId={detail.candidate?.latest_evaluation_id ?? null}
        configFields={fields}
      />

      {/* 觀察艙卡（在艙才顯示） */}
      {detail.watch && <WatchPodCard row={detail.watch} />}

      {/* 快速入口列 —— Evaluate 為主要動作 */}
      <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm">
        <button
          onClick={() => navigate(evaluateHref(detail.name))}
          className="rounded-md border border-text/40 px-3 py-1 font-medium text-text hover:bg-input"
        >
          {t('strategyHub.detail.actions.evaluate')}
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

      {/* 判決時間線（次要證據） */}
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

/**
 * 使用的資料卡 section —— 反向索引（哪些策略用某資料卡）從資料字典搬到策略側呈現。
 * 複用既有 GET /system/datasets（型錄含 used_by），前端依策略名過濾，不需新後端。
 * 空/載入/錯誤皆誠實降級：無卡 → 提示（策略只讀還原 OHLC 也屬正常）。
 */
function UsedDatasetsSection({ strategy }: { strategy: string }) {
  const { t } = useTranslation('research')
  const q = useDatasets()
  const cards = Array.isArray(q.data?.data) ? q.data.data : []
  const used = cards.filter((c) => (c.used_by ?? []).includes(strategy))

  // 型錄未載入完成前不佔版面（次要資訊，靜默）
  if (q.isLoading || q.isError) return null

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 text-xs uppercase tracking-wide text-text-muted">
        {t('strategyHub.detail.datasets.title')}
      </div>
      {used.length === 0 ? (
        <p className="text-xs text-text-muted">{t('strategyHub.detail.datasets.empty')}</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {used.map((c) => (
            <li key={c.key} className="flex flex-wrap items-baseline gap-2 text-sm">
              <span className="text-text">{c.name_zh}</span>
              <code className="font-mono text-xs text-text-muted">{c.key}</code>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/**
 * 候選生命週期 section（IA 裁決 B：候選詳情折入策略資產詳情）。
 * 四態：loading → skeleton；error → 誠實降級（非紅 banner）+ 重試；無候選 → 「尚未評估」引導；
 * 有候選 → state + profile/label + 五維燈 + next_action + 連結 + 決策軌跡（折疊，複用候選池慣例）。
 */
function CandidateLifecycle({
  candidate,
  query,
  onEvaluate,
}: {
  candidate: Candidate | null
  query: UseQueryResult<Candidate[]>
  onEvaluate: () => void
}) {
  const { t } = useTranslation('research')
  const navigate = useNavigate()
  const [showTrail, setShowTrail] = useState(false)
  const runId = candidate ? runIdFromReportRef(candidate.report_pack_ref) : null

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface">
      <div className="border-b border-border px-4 py-2 text-xs uppercase tracking-wide text-text-muted">
        {t('strategyHub.detail.candidate.title')}
      </div>

      {query.isLoading ? (
        <div className="p-4">
          <SkeletonRows rows={2} cols={3} />
        </div>
      ) : query.isError ? (
        <div className="flex flex-wrap items-center gap-3 p-4 text-xs text-text-muted">
          <span>{t('strategyHub.detail.candidate.unavailable')}</span>
          <button
            onClick={() => query.refetch()}
            className="rounded-md border border-border px-3 py-1 text-text-secondary hover:text-text"
          >
            {t('common:action.retry')}
          </button>
        </div>
      ) : !candidate ? (
        <div className="p-6 text-sm">
          <p className="font-medium text-text">{t('strategyHub.detail.candidate.empty.headline')}</p>
          <p className="mt-1 text-xs text-text-secondary">{t('strategyHub.detail.candidate.empty.subtitle')}</p>
          <button
            onClick={onEvaluate}
            className="mt-3 rounded-md border border-text/40 px-3 py-1.5 text-xs font-medium text-text hover:bg-input"
          >
            {t('strategyHub.detail.candidate.empty.cta')}
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 p-4">
          {/* state + profile + label */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <CandidateStateBadge state={candidate.state} />
            <span className="inline-flex items-center gap-1.5 text-xs">
              <span className="text-text-muted">{t('strategyHub.detail.candidate.latestProfile')}</span>
              <span className="font-mono text-text-secondary">{candidate.latest_profile}</span>
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs">
              <span className="text-text-muted">{t('strategyHub.detail.candidate.label')}</span>
              <span className="text-text-secondary">{candidate.latest_label}</span>
            </span>
          </div>

          {/* 五維 scorecard 燈 */}
          <ScorecardLights summary={candidate.scorecard_summary} />

          {/* next action */}
          <p className="text-xs text-text-secondary">
            <span className="text-text-muted">{t('strategyHub.detail.candidate.nextAction')}: </span>
            {candidate.next_action}
          </p>

          {/* 連結：Report Viewer + 候選池 + 決策軌跡切換 */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            {runId ? (
              <button
                onClick={() => navigate(`/research/reports/${runId}`)}
                className="text-text-secondary underline-offset-2 hover:text-text hover:underline"
              >
                {t('strategyHub.detail.candidate.viewReport')}
              </button>
            ) : (
              <span className="text-text-muted">{t('strategyHub.detail.candidate.noReport')}</span>
            )}
            <span className="text-text-muted" aria-hidden>·</span>
            <button
              onClick={() => navigate('/research/candidates')}
              className="text-text-secondary underline-offset-2 hover:text-text hover:underline"
            >
              {t('strategyHub.detail.candidate.viewPool')}
            </button>
            {candidate.decisions.length > 0 && (
              <>
                <span className="text-text-muted" aria-hidden>·</span>
                <button
                  onClick={() => setShowTrail((v) => !v)}
                  aria-expanded={showTrail}
                  className="text-text-secondary underline-offset-2 hover:text-text hover:underline"
                >
                  {t('strategyHub.detail.candidate.trail', { n: candidate.decisions.length })}
                </button>
              </>
            )}
          </div>

          {/* 決策軌跡（折疊，複用候選池 decisionAction i18n） */}
          {showTrail && candidate.decisions.length > 0 && (
            <ul className="flex flex-col gap-1 border-t border-border/50 pt-2 text-[11px] text-text-muted">
              {candidate.decisions.map((d) => (
                <li key={d.decision_id} className="flex flex-wrap items-baseline gap-1.5">
                  <span className="font-mono tabular">{d.at.slice(0, 10)}</span>
                  <span className="text-text-secondary">
                    {t(`candidates.decisionAction.${d.action}`, { defaultValue: d.action })}
                  </span>
                  <span aria-hidden>·</span>
                  <span className="font-mono">
                    {d.from_state}→{d.to_state}
                  </span>
                  {d.reason && <span className="italic">「{d.reason}」</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
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
