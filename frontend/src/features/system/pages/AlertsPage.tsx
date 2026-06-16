/*
 * System — 告警設定（system_alerts）。
 * 內建告警規則表（/system/alerts/rules，真實投影 §4.2）+ 風控規格計數
 * （/system/risk/spec，真實 12 條）+ 頻道設定（/system/alerts/channels，pending：
 * bot_token 一律遮罩，CRUD 待 rule store）。
 */
import { PageHeader } from '@/components/PageHeader'
import { PendingNote } from '@/components/PendingNote'
import { StatusBadge } from '@/components/StatusBadge'
import { QueryState, SimpleTable } from '@/features/monitor/components'
import type { AlertRuleRow } from '../hooks/useSystem'
import { useAlertRules, useRiskSpec } from '../hooks/useSystem'

const LEVEL_TONE: Record<string, 'error' | 'warning' | 'muted'> = {
  CRITICAL: 'error',
  HIGH: 'warning',
  INFO: 'muted',
}

export function AlertsPage() {
  const rules = useAlertRules()
  const risk = useRiskSpec()
  const riskCount = risk.data?.data?.rules?.length

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

      <PendingNote label="頻道設定 / 測試送達 / 規則 CRUD（alerts/channels · test · POST/PUT 待 rule store；bot_token 一律遮罩）" />
    </div>
  )
}
