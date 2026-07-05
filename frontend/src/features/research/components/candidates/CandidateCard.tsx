/*
 * 候選決策列 —— Candidate Pool 的主要操作單元。
 * 每列呈現 strategy / scorecard / headline risk-return / governance recommendation / next action，
 * 讓研究結果像 blotter 一樣可掃描、可追溯、可送入治理流程。
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
    <div className="grid grid-cols-[56px_1fr] items-baseline gap-2">
      <span className="text-[10px] uppercase tracking-[0.12em] text-text-muted">{label}</span>
      <span className="text-right font-mono text-[12px] tabular text-text-secondary">{value}</span>
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
    <section className="min-w-[1040px] border-b border-border bg-surface px-3 py-3 last:border-b-0 hover:bg-row lg:grid lg:grid-cols-[minmax(230px,1.25fr)_180px_190px_190px_minmax(250px,1fr)] lg:gap-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate font-mono text-[13px] font-semibold text-text">{candidate.strategy}</h3>
          <CandidateStateBadge state={candidate.state} />
          {locallyModified && <StatusBadge tone="muted">{t('candidates.localBadge')}</StatusBadge>}
        </div>
        <p className="mt-1 truncate text-xs text-text-secondary" title={candidate.hypothesis}>
          {candidate.hypothesis}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
          <span className="text-text-muted">{t('candidates.card.latestProfile')}</span>
          <span className="font-mono text-text-secondary">{candidate.latest_profile}</span>
        </div>
      </div>

      <div className="mt-3 lg:mt-0">
        <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-text-muted">Scorecard</div>
        <ScorecardLights summary={candidate.scorecard_summary} />
        {candidate.branch_origin && (
          <div className="mt-2">
            <StatusBadge tone="muted">
              <span aria-hidden>⑂ </span>
              {t('candidates.branchOrigin')}
            </StatusBadge>
          </div>
        )}
      </div>

      <div className="mt-3 border-y border-border/60 py-2 lg:mt-0 lg:border-y-0 lg:py-0">
        <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-text-muted">Return / Risk</div>
        <div className="space-y-1">
          <HeadlineStat label={t('candidates.headline.sharpe')} value={fmt(h.sharpe)} />
          <HeadlineStat label={t('candidates.headline.dsr')} value={fmt(h.dsr, 3)} />
          <HeadlineStat label={t('candidates.headline.maxdd')} value={fmtPct(h.max_drawdown)} />
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-2 lg:mt-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-text-muted">{t('candidates.recommendation.label')}</span>
          <StatusBadge tone={recommendationTone(candidate.live_oos_recommendation)}>
            {t(`candidates.recommendation.${candidate.live_oos_recommendation}`, {
              defaultValue: candidate.live_oos_recommendation,
            })}
          </StatusBadge>
        </div>
        {candidate.latest_truth_verdict && (
          <div className="flex items-center justify-between gap-2">
            <span className="text-text-muted">{t('candidates.truthVerdict.label')}</span>
            <StatusBadge tone={truthVerdictTone(candidate.latest_truth_verdict)}>
              {t(`candidates.truthVerdict.${candidate.latest_truth_verdict}`, {
                defaultValue: candidate.latest_truth_verdict,
              })}
            </StatusBadge>
          </div>
        )}
      </div>

      <div className="mt-3 lg:mt-0">
        <p className="max-h-8 overflow-hidden text-xs text-text-secondary">
          <span className="text-text-muted">{t('candidates.nextAction')}: </span>
          {candidate.next_action}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          {runId ? (
            <Link to={`/research/reports/${runId}`} className="text-info underline-offset-2 hover:underline">
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
        <div className="mt-3 flex flex-wrap gap-1.5">
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
                    ? 'border border-info/60 bg-input px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-text hover:border-info disabled:opacity-40'
                    : 'border border-border px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.08em] text-text-secondary hover:border-border-strong hover:text-text disabled:opacity-40'
                }
              >
                {t(`candidates.action.${action}`)}
              </button>
            )
          })}
        </div>
      </div>

      {showTrail && (
        <ul className="mt-3 flex flex-col gap-1 border-t border-border/50 pt-2 text-[11px] text-text-muted lg:col-span-5">
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
    </section>
  )
}
