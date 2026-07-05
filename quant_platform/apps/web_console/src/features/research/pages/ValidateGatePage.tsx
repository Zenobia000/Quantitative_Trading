/*
 * Release gate（UI route /deploy/gate?run_id=）。屬 Governance 子流程，檢查研究證據能否發布。
 * is_gate_checklist 接真實 GET /gate/spec（shipped，顯示硬門檻規格）。
 * 選定 candidate run（?run_id=）後：接真實 GET /research/validate/{id}/gate-state（validation_status
 * + stage + 轉移歷史）、GET /research/validate/{id}/wfa（IS252/OOS63 rolling fold 日期窗）
 * 與 GET /research/validate/{id}/health（13 指標 green/yellow/red 表，run metrics 投影）。
 * WFA scatter（per-fold IS/OOS 績效）需 parquet → pending；OOS vault / redline / signoff 亦 pending。
 */
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useGateSpec } from '../hooks/useGateSpec'
import { useGateState } from '../hooks/useGateState'
import { useValidateWfa } from '../hooks/useValidateWfa'
import { useValidateHealth } from '../hooks/useValidateHealth'
import type { HealthLight } from '../api/health'
import { PendingNote } from '@/components/PendingNote'
import { SkeletonRows } from '@/components/Skeleton'
import { EnumBadge } from '@/components/EnumBadge'
import { StatusBadge } from '@/components/StatusBadge'
import { useErrorText } from '@/i18n/useErrorText'

// 13 指標燈號 → StatusBadge tone。na = 缺漏指標（不靜默判綠）。
const LIGHT_TONE: Record<HealthLight, 'gain' | 'warning' | 'error' | 'muted'> = {
  green: 'gain',
  yellow: 'warning',
  red: 'error',
  na: 'muted',
}

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
  const health = useValidateHealth(runId || undefined)
  const gs = gateState.data?.data
  const folds = wfa.data?.data?.folds ?? []
  const wfaCriteria = wfa.data?.data?.criteria ?? {}
  const healthReport = health.data?.data
  const healthRows = healthReport?.rows ?? []

  return (
    <div>
      <section className="mb-3 border border-border bg-panel">
        <div className="flex flex-wrap items-start gap-3 border-b border-border px-3 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-text-muted">
              Release Gate Governance
            </div>
            <h1 className="mt-1 text-[18px] font-semibold text-text">{t('validate.title')}</h1>
            <p className="mt-1 text-xs text-text-muted">{t('validate.subtitle')}</p>
          </div>
          <div className="ml-auto font-mono text-[11px] uppercase tracking-[0.08em] text-text-muted">
            /deploy/gate
          </div>
        </div>
      </section>

      {/* candidate run selector */}
      <section className="mb-3 flex flex-wrap items-center gap-2 border border-border bg-surface p-3 text-sm">
        <label className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">{t('validate.candidateLabel')}</label>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('validate.candidatePlaceholder')}
          className="min-w-[220px] flex-1 border border-border bg-input px-3 py-1.5 font-mono text-xs"
        />
        <button
          onClick={() => setSp(input.trim() ? { run_id: input.trim() } : {})}
          className="border border-border px-3 py-1.5 text-text-secondary hover:bg-input hover:text-text"
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
      <section className="mb-3 border border-border bg-panel">
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
            {t('validate.gateChecklist.title')}
          </h2>
          <span className="ml-auto text-xs text-text-muted">{t('validate.gateChecklist.source')}</span>
        </div>
        <div className="p-3">
          {isLoading ? (
            <SkeletonRows rows={5} cols={3} />
        ) : isError ? (
          <div className="text-sm">
            <p className="text-error">
              {t('errors:load.failed', { resource: t('validate.gateSpec.resource'), detail: errText(error) })}
            </p>
            <button onClick={() => refetch()} className="mt-2 border border-border px-3 py-1 hover:bg-input hover:text-text">
              {t('common:action.retry')}
            </button>
          </div>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {criteria.map((c) => (
              <li
                key={c.key}
                className="flex items-center gap-3 border border-border/60 bg-surface px-3 py-1.5 text-sm"
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
        </div>
      </section>

      {/* gate-state history — 真實 GET /research/validate/{id}/gate-state */}
      {runId && (
        <section className="mb-3 border border-border bg-panel">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
              {t('validate.history.title')}
            </h2>
            <span className="ml-auto text-xs text-text-muted">{t('validate.history.source')}</span>
          </div>
          <div className="p-3">
            {gateState.isLoading ? (
              <SkeletonRows rows={2} cols={2} />
          ) : (gs?.history ?? []).length === 0 ? (
            <p className="text-sm text-text-muted">{t('validate.history.empty')}</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {(gs?.history ?? []).map((ev, i) => (
                <li key={i} className="flex items-center gap-3 border border-border/60 bg-surface px-3 py-1.5 text-sm">
                  <EnumBadge family="validation" value={ev.validation_status} />
                  <EnumBadge family="stage" value={ev.stage} />
                  <span className="ml-auto font-mono text-xs text-text-muted tabular">{ev.at}</span>
                </li>
              ))}
            </ul>
          )}
          </div>
        </section>
      )}

      {/* WFA folds — 真實 GET /research/validate/{id}/wfa（folds data-free；scatter pending） */}
      {runId && (
        <section className="mb-3 border border-border bg-panel">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
              {t('validate.wfa.title')}
            </h2>
            <span className="ml-auto text-xs text-text-muted">{t('validate.wfa.window')}</span>
          </div>
          <div className="p-3">
            {wfa.isLoading ? (
              <SkeletonRows rows={3} cols={4} />
          ) : folds.length === 0 ? (
            <p className="text-sm text-text-muted">{t('validate.wfa.empty')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b border-border bg-base text-left font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                    <th className="p-2 font-medium">#</th>
                    <th className="p-2 font-medium">IS</th>
                    <th className="p-2 font-medium">OOS</th>
                  </tr>
                </thead>
                <tbody>
                  {folds.map((f) => (
                    <tr key={f.fold} className="border-b border-border/60 bg-surface hover:bg-row">
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
          </div>
        </section>
      )}

      {/* 13 指標健康表 — 真實 GET /research/validate/{id}/health（run metrics 投影） */}
      {runId && (
        <section className="mb-3 border border-border bg-panel">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
              {t('validate.health.title')}
            </h2>
            <span className="ml-auto text-xs text-text-muted">{t('validate.health.window')}</span>
          </div>
          <div className="p-3">
            {health.isLoading ? (
              <SkeletonRows rows={4} cols={3} />
            ) : healthRows.length === 0 ? (
              <p className="text-sm text-text-muted">{t('validate.health.empty')}</p>
            ) : (
              <>
                <div className="mb-2 font-mono text-[11px] text-text-secondary">
                  {t('validate.health.counts', {
                    green: healthReport?.counts.green ?? 0,
                    yellow: healthReport?.counts.yellow ?? 0,
                    red: healthReport?.counts.red ?? 0,
                    na: healthReport?.counts.na ?? 0,
                  })}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[420px] text-sm">
                    <thead>
                      <tr className="border-b border-border bg-base text-left font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                        <th className="p-2 font-medium">{t('validate.health.colIndicator')}</th>
                        <th className="p-2 text-right font-medium">{t('validate.health.colValue')}</th>
                        <th className="p-2 font-medium">{t('validate.health.colLight')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {healthRows.map((r) => (
                        <tr key={r.key} className="border-b border-border/60 bg-surface hover:bg-row">
                          <td className="p-2 text-text-secondary">{r.label}</td>
                          <td className="p-2 text-right font-mono tabular">
                            {r.value == null ? '—' : r.value}
                          </td>
                          <td className="p-2">
                            <StatusBadge tone={LIGHT_TONE[r.light]}>{r.light.toUpperCase()}</StatusBadge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
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
