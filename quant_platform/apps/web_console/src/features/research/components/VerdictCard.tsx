/*
 * 判決卡（置頂，本平台差異化）—— 觀察艙三個月的日常入口第一眼。
 * gate_status 大 badge（PASS/FAIL/INCOMPLETE）+ criteria 燈號列（各準則對 run.metrics 現值評估）
 * + DSR 標尺（真偽閘）。criteria 缺策略宣告 → 說明；metric 缺 → 該燈不亮（誠實未知）。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { useEnumLabel } from '@/i18n/useEnumLabel'
import type { Tone } from '@/i18n/displayMap'
import type { GateCriterion, ReportVerdict } from '../api/report'
import { evalCriterion } from '../lib/reportViz'
import { DsrRuler } from './DsrRuler'

/** 大 badge tone → 邊框/文字 class（比 StatusBadge 放大，判決卡的視覺錨點）。 */
const BIG: Record<Tone, string> = {
  gain: 'border-gain/50 text-gain',
  loss: 'border-loss/50 text-loss',
  warning: 'border-warning/50 text-warning',
  error: 'border-error/50 text-error',
  muted: 'border-border text-text-muted',
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

function CriterionLight({
  criterion,
  metrics,
}: {
  criterion: GateCriterion
  metrics: Record<string, unknown>
}) {
  const value = num(metrics[criterion.key])
  const pass = evalCriterion(value, criterion.op, criterion.threshold)
  const tone: Tone = pass === null ? 'muted' : pass ? 'gain' : 'loss'
  const mark = pass === null ? '○' : pass ? '✓' : '✗'
  return (
    <StatusBadge tone={tone}>
      <span aria-hidden>{mark}</span>
      <span>{criterion.label}</span>
      <span className="font-mono text-[10px] text-text-muted tabular">
        {value == null ? '—' : value.toFixed(2)} {criterion.op} {criterion.threshold}
      </span>
    </StatusBadge>
  )
}

export function VerdictCard({
  verdict,
  gateStatusFallback,
  metrics,
}: {
  verdict: ReportVerdict | null | undefined
  /** report 尚未載入時退回 run.gate_status（同一 record 來源）。 */
  gateStatusFallback: string | null
  metrics: Record<string, unknown>
}) {
  const { t } = useTranslation('research')
  const gateStatus = verdict?.gate_status ?? gateStatusFallback
  const { label, tone } = useEnumLabel('gate', gateStatus)
  const criteria = verdict?.criteria ?? null

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <span className="text-xs text-text-muted">{t('report.gateLabel')}</span>
        <span
          className={`inline-flex items-center rounded-md border px-3 py-1 text-lg font-semibold ${BIG[tone]}`}
        >
          {label}
        </span>
      </div>

      {/* criteria 燈號列 */}
      <div className="mb-4">
        <div className="mb-1.5 text-xs text-text-muted">{t('report.verdict.criteriaTitle')}</div>
        {criteria && criteria.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {criteria.map((c) => (
              <CriterionLight key={c.key} criterion={c} metrics={metrics} />
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-muted">{t('report.verdict.noCriteria')}</p>
        )}
      </div>

      {/* DSR 標尺（真偽閘） */}
      <DsrRuler truthGate={verdict?.truth_gate} />
    </section>
  )
}
