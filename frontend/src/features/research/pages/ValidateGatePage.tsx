/*
 * Validate gate（/research/validate?run_id=）。三源對齊 assembly + design.pen frame + page spec。
 * is_gate_checklist 接真實 GET /gate/spec（shipped，顯示硬門檻規格）。
 * 選定 candidate run（?run_id=）後：接真實 GET /research/validate/{id}/gate-state（validation_status
 * + stage + 轉移歷史）與 GET /research/validate/{id}/wfa（IS252/OOS63 rolling fold 日期窗）。
 * WFA scatter（per-fold IS/OOS 績效）需 parquet → pending；OOS vault / redline / signoff 亦 pending。
 */
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useGateSpec } from '../hooks/useGateSpec'
import { useGateState } from '../hooks/useGateState'
import { useValidateWfa } from '../hooks/useValidateWfa'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { useErrorText } from '@/i18n/useErrorText'

export function ValidateGatePage() {
  const { t } = useTranslation('research')
  const errText = useErrorText()
  const navigate = useNavigate()
  const [sp, setSp] = useSearchParams()
  const runId = sp.get('run_id') ?? ''
  const [input, setInput] = useState(runId)

  const { data, isLoading, isError, error, refetch } = useGateSpec()
  const criteria = data?.data?.criteria ?? []

  const gateState = useGateState(runId || undefined)
  const wfa = useValidateWfa(runId || undefined)
  const gs = gateState.data?.data
  const folds = wfa.data?.data?.folds ?? []
  const wfaCriteria = wfa.data?.data?.criteria ?? {}

  return (
    <div>
      <PageHeader
        title={t('validate.title')}
        route="/research/validate"
        subtitle={t('validate.subtitle')}
      />

      {/* candidate run selector */}
      <section className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-3 text-sm">
        <label className="text-xs text-text-secondary">{t('validate.candidateLabel')}</label>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('validate.candidatePlaceholder')}
          className="min-w-[220px] flex-1 rounded-md border border-border bg-input px-3 py-1.5 font-mono text-xs"
        />
        <button
          onClick={() => setSp(input.trim() ? { run_id: input.trim() } : {})}
          className="rounded-md border border-border px-3 py-1.5 text-text-secondary hover:text-text"
        >
          {t('validate.load')}
        </button>
        <button
          onClick={() => navigate('/research/runs')}
          className="text-xs text-text-muted hover:text-text"
        >
          {t('validate.pickFromRuns')}
        </button>
        {gs && (
          <span className="flex items-center gap-1.5">
            <EnumBadge family="validation" value={gs.validation_status ?? 'draft'} />
            <EnumBadge family="stage" value={gs.stage} />
          </span>
        )}
      </section>

      {/* gate_status_header — 需 candidate run */}
      {!runId && (
        <div className="mb-3">
          <PendingNote label={t('validate.pending.gateHeader')} />
        </div>
      )}

      {/* is_gate_checklist — 真實 GET /gate/spec */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-[18px] font-semibold">{t('validate.gateChecklist.title')}</h2>
          <span className="text-xs text-text-muted">{t('validate.gateChecklist.source')}</span>
        </div>
        {isLoading ? (
          <SkeletonRows rows={5} cols={3} />
        ) : isError ? (
          <div className="text-sm">
            <p className="text-error">
              {t('errors:load.failed', { resource: t('validate.gateSpec.resource'), detail: errText(error) })}
            </p>
            <button onClick={() => refetch()} className="mt-2 rounded-md border border-border px-3 py-1 hover:text-text">
              {t('common:action.retry')}
            </button>
          </div>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {criteria.map((c) => (
              <li
                key={c.key}
                className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-1.5 text-sm"
              >
                <EnumBadge family="criterion" value={c.kind} />
                <span className="text-text">{c.label}</span>
                <span className="ml-auto font-mono text-xs text-text-secondary tabular">
                  {c.key} {c.op} {c.threshold}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* gate-state history — 真實 GET /research/validate/{id}/gate-state */}
      {runId && (
        <section className="mb-3 rounded-lg border border-border bg-surface p-4">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-[18px] font-semibold">{t('validate.history.title')}</h2>
            <span className="text-xs text-text-muted">{t('validate.history.source')}</span>
          </div>
          {gateState.isLoading ? (
            <SkeletonRows rows={2} cols={2} />
          ) : (gs?.history ?? []).length === 0 ? (
            <p className="text-sm text-text-muted">{t('validate.history.empty')}</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {(gs?.history ?? []).map((ev, i) => (
                <li key={i} className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-1.5 text-sm">
                  <EnumBadge family="validation" value={ev.validation_status} />
                  <EnumBadge family="stage" value={ev.stage} />
                  <span className="ml-auto font-mono text-xs text-text-muted tabular">{ev.at}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* WFA folds — 真實 GET /research/validate/{id}/wfa（folds data-free；scatter pending） */}
      {runId && (
        <section className="mb-3 rounded-lg border border-border bg-surface p-4">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-[18px] font-semibold">{t('validate.wfa.title')}</h2>
            <span className="text-xs text-text-muted">{t('validate.wfa.window')}</span>
          </div>
          {wfa.isLoading ? (
            <SkeletonRows rows={3} cols={4} />
          ) : folds.length === 0 ? (
            <p className="text-sm text-text-muted">{t('validate.wfa.empty')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-muted">
                    <th className="p-2 font-medium">#</th>
                    <th className="p-2 font-medium">IS</th>
                    <th className="p-2 font-medium">OOS</th>
                  </tr>
                </thead>
                <tbody>
                  {folds.map((f) => (
                    <tr key={f.fold} className="border-b border-border/60">
                      <td className="p-2 font-mono tabular text-text-muted">{f.fold}</td>
                      <td className="p-2 font-mono text-xs tabular">{f.is_start} ~ {f.is_end}</td>
                      <td className="p-2 font-mono text-xs tabular">{f.oos_start} ~ {f.oos_end}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {Object.keys(wfaCriteria).length > 0 && (
            <ul className="mt-3 flex flex-col gap-1 text-xs text-text-secondary">
              {Object.entries(wfaCriteria).map(([k, v]) => (
                <li key={k}>· {String(v)}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* 仍需後端／parquet 的階段 */}
      <div className="flex flex-col gap-2">
        <PendingNote label={t('validate.pending.scatter')} />
        <PendingNote label={t('validate.pending.vault')} />
        <PendingNote label={t('validate.pending.redline')} />
        <PendingNote label={t('validate.pending.signoff')} />
      </div>
    </div>
  )
}
