/*
 * Evidence / gate checks —— deployment_strict 的 hard-fail 燈號（契約 checks[]）。
 * 頂端複用 DsrRuler（真偽閘視覺錨點：DSR 指針 + band），下方逐條 check：狀態燈 + severity chip
 * （block_deploy 紅 / block_live_oos 琥珀 / info 中性）+ 值/門檻 + 原因。誠實揭露唯一 deploy-blocking 失敗。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { DsrRuler } from '../DsrRuler'
import type { GateCheck } from '../../api/reportViewer'
import { severityTone, statusMark, statusTone, truthVerdictToBand } from '../../lib/scorecardStatus'

/** check 的值 / 門檻顯示（bool → is_true/false；數字 → 4 位；null → 破折號）。 */
function fmtCheckOperand(v: number | boolean | null): string {
  if (v == null) return '—'
  if (typeof v === 'boolean') return String(v)
  return Number.isInteger(v) ? String(v) : v.toFixed(4)
}

export function GateChecksSection({
  checks,
  dsr,
  truthVerdict,
}: {
  checks: GateCheck[]
  dsr: number | null
  truthVerdict: string
}) {
  const { t } = useTranslation('research')
  const band = truthVerdictToBand(truthVerdict)

  return (
    <section className="mb-3 rounded-lg border border-border bg-surface p-4">
      <div className="mb-3">
        <h2 className="text-[18px] font-semibold">{t('reportViewer.checks.title')}</h2>
        <p className="text-xs text-text-muted">{t('reportViewer.checks.subtitle')}</p>
      </div>

      {/* 真偽閘標尺（複用 F1 DsrRuler） */}
      <div className="mb-4">
        <DsrRuler truthGate={{ verdict_dsr: dsr, band }} />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="py-1.5 pr-3 font-medium">{t('reportViewer.scorecard.statusCol')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('reportViewer.checks.metricCol')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('reportViewer.scorecard.valueCol')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('reportViewer.scorecard.thresholdCol')}</th>
              <th className="py-1.5 pr-3 font-medium">{t('reportViewer.checks.severityCol')}</th>
              <th className="py-1.5 font-medium">{t('reportViewer.scorecard.reasonCol')}</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c) => (
              <tr key={c.metric} className="border-b border-border/40 align-top">
                <td className="py-1.5 pr-3">
                  <StatusBadge tone={statusTone(c.status)}>
                    <span aria-hidden>{statusMark(c.status)}</span>
                    <span>{t(`reportViewer.status.${c.status}`)}</span>
                  </StatusBadge>
                </td>
                <td className="py-1.5 pr-3 font-mono tabular text-text">{c.metric}</td>
                <td className="py-1.5 pr-3 font-mono tabular text-text">{fmtCheckOperand(c.value)}</td>
                <td className="py-1.5 pr-3 font-mono tabular text-text-secondary">
                  {c.op} {fmtCheckOperand(c.threshold)}
                </td>
                <td className="py-1.5 pr-3">
                  <StatusBadge tone={severityTone(c.severity)}>
                    {t(`reportViewer.checks.severity.${c.severity}`, { defaultValue: c.severity })}
                  </StatusBadge>
                </td>
                <td className="py-1.5 text-xs text-text-muted">{c.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
