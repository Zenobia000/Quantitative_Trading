/*
 * System-zone hooks — read config/manifest (useEndpoint) + ingest mutation/poll.
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { getIngestStatus, triggerIngest } from '../api/ingest'
import type { IngestBody } from '../api/ingest'
import { getUniverseBuildStatus, triggerUniverseBuild } from '../api/universe'
import type { UniverseBuildBody } from '../api/universe'
import { useEndpoint } from '@/hooks/useEndpoint'
import type { components } from '@/types/api.gen'

export interface AlertRuleRow {
  rule_id: string
  level: string
  title: string
}

/** GET /system/alerts/channels — bot_token 一律遮罩（rules/security.md §4）。 */
export interface AlertChannels {
  discord?: { enabled?: boolean; bot_token?: string }
}

/** GET /system/bundles row — 形狀由 OpenAPI 生成（禁手寫，doc 25）。 */
export type BundleRow = components['schemas']['BundleRow']

/** GET /system/bundles — 真實 manifest 掃描（無 manifest → typed-empty，非假造）。 */
export const useBundles = () => useEndpoint<BundleRow[]>('/system/bundles', 300)
export const useAlertRules = () => useEndpoint<AlertRuleRow[]>('/system/alerts/rules', 300)
export const useAlertChannels = () => useEndpoint<AlertChannels>('/system/alerts/channels', 300)
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

/** Trigger a survivorship-clean universe build (async job, ADR-032). */
export const useTriggerUniverseBuild = () =>
  useMutation({ mutationFn: (body: UniverseBuildBody) => triggerUniverseBuild(body) })

/** Poll a universe-build job's status until terminal (done/failed). */
export const useUniverseBuildStatus = (jobId: string | null) =>
  useQuery({
    queryKey: ['universe-build-status', jobId],
    queryFn: () => getUniverseBuildStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.data?.status
      return s === 'done' || s === 'failed' ? false : 1000
    },
  })
