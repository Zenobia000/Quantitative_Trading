/*
 * System — 告警設定（system_alerts）。
 * 內建告警規則表（/system/alerts/rules，真實投影 §4.2）+ 風控規格計數
 * （/system/risk/spec，真實 12 條）+ 頻道設定（/system/alerts/channels，shipped：
 * discord enabled + bot_token 一律遮罩）。CRUD（PUT/POST 規則、測試送達、history）待 rule store → pending。
 */
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { StatusBadge } from '@/components/StatusBadge'
import { QueryState, SimpleTable } from '@/features/monitor/components'
import type { AlertRuleRow } from '../hooks/useSystem'
import { useAlertChannels, useAlertRules, useRiskSpec } from '../hooks/useSystem'

// 級別 → tone（TS，色彩雙編碼；文字標籤本地化，無 severity enum family → 見 system:alerts.level）
const LEVEL_TONE: Record<string, 'error' | 'warning' | 'muted'> = {
  CRITICAL: 'error',
  HIGH: 'warning',
  INFO: 'muted',
}

export function AlertsPage() {
  const { t } = useTranslation('system')
  const rules = useAlertRules()
  const risk = useRiskSpec()
  const channels = useAlertChannels()
  const riskCount = risk.data?.data?.rules?.length
  const discord = channels.data?.data?.discord

  return (
    <div>
      <PageHeader title={t('alerts.title')} route="/system/alerts" subtitle={t('alerts.subtitle')} />

      <section className="mb-3">
        <div className="mb-1 flex items-center gap-2 text-xs text-text-muted">
          {t('alerts.rules.heading')}
          {typeof riskCount === 'number' && (
            <StatusBadge tone="muted">{t('alerts.rules.riskCount', { n: riskCount })}</StatusBadge>
          )}
        </div>
        <QueryState q={rules} pendingLabel={t('alerts.rules.pending')} emptyLabel={t('alerts.rules.empty')}>
          {(rows: AlertRuleRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'rule_id', label: t('alerts.rules.col.ruleId') },
                {
                  key: 'level',
                  label: t('alerts.rules.col.level'),
                  fmt: (v) => (
                    <StatusBadge tone={LEVEL_TONE[String(v)] ?? 'muted'}>
                      {t(`alerts.level.${String(v)}`, { defaultValue: String(v) })}
                    </StatusBadge>
                  ),
                },
                { key: 'title', label: t('alerts.rules.col.title') },
              ]}
            />
          )}
        </QueryState>
      </section>

      {/* 頻道設定（shipped，遮罩） */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 text-xs text-text-muted">{t('alerts.channels.heading')}</div>
        {discord ? (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge tone={discord.enabled ? 'gain' : 'muted'}>
              Discord {discord.enabled ? t('alerts.channels.enabled') : t('alerts.channels.disabled')}
            </StatusBadge>
            <span className="font-mono text-xs text-text-secondary">bot_token: {discord.bot_token ?? '***'}</span>
          </div>
        ) : (
          <p className="text-sm text-text-muted">{t('alerts.channels.none')}</p>
        )}
      </section>

      <PendingNote label={t('alerts.pending')} />
    </div>
  )
}
