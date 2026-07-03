/*
 * 首頁 · 控制塔（/）。三源對齊 assembly + design.pen frame + page spec。
 * research_status + recent_activity 接真實 /home/*（read_runs 聚合）；
 * fleet_strip + system_health 需 live 資料（M4）→ pending（不假造數字）。
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useRecent, useResearchStatus } from '../hooks/useHome'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { Skeleton } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { EnumBadge } from '@/components/EnumBadge'
import { StatCard } from '@/components/StatCard'
import { FirstRunEmptyState } from '@/components/FirstRunEmptyState'
import { useErrorText } from '@/i18n/useErrorText'

export function HomePage() {
  const navigate = useNavigate()
  const { t } = useTranslation(['home', 'nav'])
  const errText = useErrorText()
  const rs = useResearchStatus()
  const rec = useRecent()
  const status = rs.data?.data
  const recent = rec.data?.data ?? []
  const isNewPlatform = status?.total_runs === 0 && !rs.isLoading

  return (
    <div>
      <PageHeader title={t('title')} route="/" subtitle={t('subtitle')} />

      {/* command_hero — primary 動作前置。⌘K 已在 topbar，這裡不放死鈕；
          新建回測 為顯眼 primary，其餘為研究迴圈次要快捷。 */}
      <div className="mb-4 rounded-lg border border-border bg-surface px-5 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="mr-auto">
            <div className="text-sm font-medium text-text">{t('hero.headline')}</div>
            <div className="text-xs text-text-muted">{t('hero.flow')}</div>
          </div>
          <button
            onClick={() => navigate('/research/runs/new')}
            className="rounded-pill bg-text px-5 py-2 text-sm font-medium text-base hover:opacity-90"
          >
            {t('hero.cta')}
          </button>
        </div>
        {/* workflow ribbon — 對齊新 IA 三旅程軸：研究 triage → 候選池 → Live OOS → 部署（rebuild IA §1.0） */}
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            { label: t('nav:item.strategies'), to: '/research/strategies' },
            { label: t('nav:item.candidates'), to: '/research/candidates' },
            { label: t('nav:item.liveOosQueue'), to: '/live-oos/queue' },
            { label: t('nav:item.strictGate'), to: '/deploy/gate' },
          ].map((q) => (
            <button
              key={q.to}
              onClick={() => navigate(q.to)}
              className="rounded-md border border-border px-3 py-1 text-sm text-text-secondary hover:text-text"
            >
              {q.label}
            </button>
          ))}
        </div>
      </div>

      {isNewPlatform ? (
        <FirstRunEmptyState headline={t('welcome')} onCta={() => navigate('/research/runs/new')} />
      ) : (
        <>
          {/* research_status — 真實資料前置（live 數據領先，避免夾在 pending 之間） */}
          <section className="mb-3">
            <h2 className="mb-2 text-sm text-text-secondary">{t('researchStatus')}</h2>
            {rs.isLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : rs.isError ? (
              <div className="rounded-lg border border-border bg-surface p-4 text-sm text-error">
                {t('errors:load.failed', { resource: t('researchStatus'), detail: errText(rs.error) })}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <StatCard label={t('kpi.totalRuns')} value={status?.total_runs ?? '—'} />
                <StatCard
                  label={t('kpi.latestGate')}
                  value={
                    status?.latest_gate_status ? (
                      <EnumBadge family="gate" value={status.latest_gate_status} />
                    ) : (
                      '—'
                    )
                  }
                />
                <StatCard label={t('kpi.trials')} value={status?.trials ?? t('common:state.awaitingBackend')} />
                <StatCard label={t('kpi.dsr')} value={status?.dsr ?? t('common:state.awaitingBackend')} />
              </div>
            )}
          </section>

          {/* recent_activity — 真接 */}
          <section className="mb-3">
            <h2 className="mb-2 text-sm text-text-secondary">{t('recentActivity')}</h2>
            {rec.isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : recent.length === 0 ? (
              <div className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">{t('noRecent')}</div>
            ) : (
              <ul className="flex flex-col gap-1">
                {recent.map((r, i) => (
                  <li
                    key={i}
                    onClick={() => r.run_id && navigate(`/research/runs/${encodeURIComponent(r.run_id)}`)}
                    className="flex cursor-pointer items-center gap-3 rounded-md border border-border/60 bg-surface px-3 py-1.5 text-sm hover:bg-input"
                  >
                    <StatusBadge tone="muted">{r.type}</StatusBadge>
                    <span className="font-mono text-xs tabular">{r.run_id}</span>
                    <span className="text-text-secondary">{r.preset}</span>
                    {r.gate_status && (
                      <span className="ml-auto">
                        <EnumBadge family="gate" value={r.gate_status} />
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 尚未接線（M4 producer）—— 集中置底，不夾在真實數據間造成「未完工」錯覺 */}
          <div className="flex flex-col gap-2">
            <PendingNote label={t('pending.fleet')} />
            <PendingNote label={t('pending.systemHealth')} />
          </div>
        </>
      )}
    </div>
  )
}
