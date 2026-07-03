/*
 * 候選卡 —— Candidate Pool 的主要決策單元。
 * 策略名 + hypothesis 一行 + 狀態 badge + 五維 scorecard 摘要燈 + headline（Sharpe/DSR/MaxDD, tabular）
 * + latest profile + Live-OOS 建議 + 部署判決（資訊態，不放 promote）+ next_action。
 * 動作：Keep / Archive / Rerun / Select Live OOS（強制理由由頁面攔截）。
 * 連結：Report Viewer /research/reports/:runId（G5 平行建置）+ 策略資產 /research/strategies/:name。
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { CandidateStateBadge } from './CandidateStateBadge'
import { ScorecardLights } from './ScorecardLights'
import {
  actionEnabled,
  recommendationTone,
  runIdFromReportRef,
  truthVerdictTone,
  type CandidateAction,
} from './candidateDisplay'
import type { Candidate } from '../../api/candidates'

const ACTIONS: CandidateAction[] = ['keep', 'select_live_oos', 'rerun', 'archive']

function fmt(v: number | null | undefined, digits = 2): string {
  return v == null ? '—' : v.toFixed(digits)
}
function fmtPct(v: number | null | undefined): string {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}

function HeadlineStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-text-muted">{label}</span>
      <span className="font-mono text-sm tabular text-text-secondary">{value}</span>
    </div>
  )
}

export function CandidateCard({
  candidate,
  locallyModified,
  onAction,
}: {
  candidate: Candidate
  locallyModified: boolean
  onAction: (action: CandidateAction) => void
}) {
  const { t } = useTranslation('research')
  const [showTrail, setShowTrail] = useState(false)
  const runId = runIdFromReportRef(candidate.report_pack_ref)
  const h = candidate.headline

  return (
    <section className="flex flex-col rounded-lg border border-border bg-surface p-4">
      {/* header */}
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-semibold">{candidate.strategy}</h3>
        <CandidateStateBadge state={candidate.state} />
        {candidate.branch_origin && (
          <StatusBadge tone="muted">
            <span aria-hidden>⑂ </span>
            {t('candidates.branchOrigin')}
          </StatusBadge>
        )}
        {locallyModified && <StatusBadge tone="muted">{t('candidates.localBadge')}</StatusBadge>}
        {candidate.latest_truth_verdict && (
          <span className="ml-auto inline-flex items-center gap-1 text-[11px] text-text-muted">
            <span>{t('candidates.truthVerdict.label')}</span>
            <StatusBadge tone={truthVerdictTone(candidate.latest_truth_verdict)}>
              {t(`candidates.truthVerdict.${candidate.latest_truth_verdict}`, {
                defaultValue: candidate.latest_truth_verdict,
              })}
            </StatusBadge>
          </span>
        )}
      </div>

      {/* hypothesis */}
      <p className="mt-1 truncate text-xs text-text-secondary" title={candidate.hypothesis}>
        {candidate.hypothesis}
      </p>

      {/* scorecard mini five-lights */}
      <div className="mt-3">
        <ScorecardLights summary={candidate.scorecard_summary} />
      </div>

      {/* headline metrics */}
      <div className="mt-3 grid grid-cols-3 gap-2 border-y border-border/50 py-2">
        <HeadlineStat label={t('candidates.headline.sharpe')} value={fmt(h.sharpe)} />
        <HeadlineStat label={t('candidates.headline.dsr')} value={fmt(h.dsr, 3)} />
        <HeadlineStat label={t('candidates.headline.maxdd')} value={fmtPct(h.max_drawdown)} />
      </div>

      {/* profile + recommendation */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
        <span className="text-text-muted">{t('candidates.card.latestProfile')}</span>
        <span className="font-mono text-text-secondary">{candidate.latest_profile}</span>
        <span className="ml-auto inline-flex items-center gap-1">
          <span className="text-text-muted">{t('candidates.recommendation.label')}</span>
          <StatusBadge tone={recommendationTone(candidate.live_oos_recommendation)}>
            {t(`candidates.recommendation.${candidate.live_oos_recommendation}`, {
              defaultValue: candidate.live_oos_recommendation,
            })}
          </StatusBadge>
        </span>
      </div>

      {/* next action */}
      <p className="mt-2 text-xs text-text-secondary">
        <span className="text-text-muted">{t('candidates.nextAction')}: </span>
        {candidate.next_action}
      </p>

      {/* links */}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
        {runId ? (
          <Link to={`/research/reports/${runId}`} className="text-text-secondary underline-offset-2 hover:text-text hover:underline">
            {t('candidates.card.viewReport')}
          </Link>
        ) : (
          <span className="text-text-muted">{t('candidates.card.noReport')}</span>
        )}
        <span className="text-text-muted" aria-hidden>·</span>
        <Link
          to={`/research/strategies/${encodeURIComponent(candidate.strategy)}`}
          className="text-text-secondary underline-offset-2 hover:text-text hover:underline"
        >
          {t('candidates.card.viewStrategy')}
        </Link>
        {candidate.decisions.length > 0 && (
          <>
            <span className="text-text-muted" aria-hidden>·</span>
            <button
              onClick={() => setShowTrail((v) => !v)}
              aria-expanded={showTrail}
              className="text-text-secondary underline-offset-2 hover:text-text hover:underline"
            >
              {t('candidates.card.decisions', { n: candidate.decisions.length })}
            </button>
          </>
        )}
      </div>

      {/* decisions trail */}
      {showTrail && (
        <ul className="mt-2 flex flex-col gap-1 border-t border-border/50 pt-2 text-[11px] text-text-muted">
          {candidate.decisions.map((d) => (
            <li key={d.decision_id} className="flex flex-wrap items-baseline gap-1.5">
              <span className="font-mono tabular">{d.at.slice(0, 10)}</span>
              <span className="text-text-secondary">
                {t(`candidates.decisionAction.${d.action}`, { defaultValue: d.action })}
              </span>
              <span aria-hidden>·</span>
              <span className="font-mono">{d.from_state}→{d.to_state}</span>
              {d.reason && <span className="italic">「{d.reason}」</span>}
            </li>
          ))}
        </ul>
      )}

      {/* actions */}
      <div className="mt-3 flex flex-wrap gap-2 border-t border-border/50 pt-3">
        {ACTIONS.map((action) => {
          const enabled = actionEnabled(candidate, action)
          const primary = action === 'select_live_oos'
          return (
            <button
              key={action}
              onClick={() => onAction(action)}
              disabled={!enabled}
              className={
                primary
                  ? 'rounded-md border border-text/40 px-3 py-1.5 text-xs font-medium text-text hover:bg-input disabled:opacity-40'
                  : 'rounded-md border border-border px-3 py-1.5 text-xs text-text-secondary hover:text-text disabled:opacity-40'
              }
            >
              {t(`candidates.action.${action}`)}
            </button>
          )
        })}
      </div>
    </section>
  )
}
