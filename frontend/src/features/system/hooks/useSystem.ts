/*
 * System-zone hooks — read config/manifest (useEndpoint) + ingest mutation/poll.
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { getIngestStatus, triggerIngest } from '../api/ingest'
import type { IngestBody } from '../api/ingest'
import { useEndpoint } from '@/hooks/useEndpoint'

export interface AlertRuleRow {
  rule_id: string
  level: string
  title: string
}

export const useBundles = () => useEndpoint<unknown[]>('/system/bundles', 300)
export const useAlertRules = () => useEndpoint<AlertRuleRow[]>('/system/alerts/rules', 300)
export const useAlertChannels = () => useEndpoint<Record<string, unknown>>('/system/alerts/channels', 300)
export const useRiskSpec = () => useEndpoint<{ rules?: unknown[] }>('/system/risk/spec', 300)

/** Trigger an async ingest job; returns the job ref ({job_id,status}). */
export const useTriggerIngest = () =>
  useMutation({ mutationFn: (body: IngestBody) => triggerIngest(body) })

/** Poll an ingest job's status until terminal (done/failed). */
export const useIngestStatus = (jobId: string | null) =>
  useQuery({
    queryKey: ['ingest-status', jobId],
    queryFn: () => getIngestStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.data?.status
      return s === 'done' || s === 'failed' ? false : 1000
    },
  })
