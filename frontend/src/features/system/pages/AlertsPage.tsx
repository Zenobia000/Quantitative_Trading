/*
 * System — 告警設定（system_alerts）。
 * 內建告警規則表（/system/alerts/rules，真實投影 §4.2）+ 風控規格計數
 * （/system/risk/spec，真實 12 條）+ 頻道設定（/system/alerts/channels，shipped：
 * discord enabled + bot_token 一律遮罩）。CRUD（PUT/POST 規則、測試送達、history）待 rule store → pending。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { StatusBadge } from '@/components/StatusBadge'
import { QueryState, SimpleTable } from '@/features/monitor/components'
import type { AlertRuleRow } from '../hooks/useSystem'
import { useAlertChannels, useAlertRules, useRiskSpec } from '../hooks/useSystem'

const LEVEL_TONE: Record<string, 'error' | 'warning' | 'muted'> = {
  CRITICAL: 'error',
  HIGH: 'warning',
  INFO: 'muted',
}

export function AlertsPage() {
  const rules = useAlertRules()
  const risk = useRiskSpec()
  const channels = useAlertChannels()
  const riskCount = risk.data?.data?.rules?.length
  const discord = channels.data?.data?.discord

  return (
    <div>
      <PageHeader title="告警設定" route="/system/alerts" subtitle="內建告警規則 + 風控規格（config，非 telemetry）" />

      <section className="mb-3">
        <div className="mb-1 flex items-center gap-2 text-xs text-text-muted">
          告警規則（內建）
          {typeof riskCount === 'number' && <StatusBadge tone="muted">風控規格 {riskCount} 條</StatusBadge>}
        </div>
        <QueryState q={rules} pendingLabel="告警規則" emptyLabel="尚無規則">
          {(rows: AlertRuleRow[]) => (
            <SimpleTable
              rows={rows}
              cols={[
                { key: 'rule_id', label: '規則' },
                {
                  key: 'level',
                  label: '級別',
                  fmt: (v) => <StatusBadge tone={LEVEL_TONE[String(v)] ?? 'muted'}>{String(v)}</StatusBadge>,
                },
                { key: 'title', label: '說明' },
              ]}
            />
          )}
        </QueryState>
      </section>

      {/* 頻道設定（shipped，遮罩） */}
      <section className="mb-3 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 text-xs text-text-muted">通知頻道（GET /system/alerts/channels · bot_token 遮罩）</div>
        {discord ? (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge tone={discord.enabled ? 'gain' : 'muted'}>
              Discord {discord.enabled ? '已啟用' : '未啟用'}
            </StatusBadge>
            <span className="font-mono text-xs text-text-secondary">bot_token: {discord.bot_token ?? '***'}</span>
          </div>
        ) : (
          <p className="text-sm text-text-muted">尚未設定通知頻道。</p>
        )}
      </section>

      <PendingNote label="頻道編輯 / 測試送達 / 規則 CRUD（PUT channels · POST test · POST/PUT rules 待 rule store）" />
    </div>
  )
}
