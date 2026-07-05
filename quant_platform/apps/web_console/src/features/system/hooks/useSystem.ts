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

/** GET /system/datasets card — 策略作者的資料字典列（形狀由 OpenAPI 生成，禁手寫）。 */
export type DatasetCard = components['schemas']['DatasetCard']

/** GET /system/universes row — 具名股票池（ADR-007；形狀由 OpenAPI 生成，禁手寫）。 */
export type UniverseRow = components['schemas']['UniverseRow']

/** GET /system/bundles — 真實 manifest 掃描（無 manifest → typed-empty，非假造）。 */
export const useBundles = () => useEndpoint<BundleRow[]>('/system/bundles', 300)

/** GET /system/universes — 具名股票池清單（New Run 選單來源；ttl 300s）。 */
export const useUniverses = () => useEndpoint<UniverseRow[]>('/system/universes', 300)

/**
 * GET /system/datasets — FinLab 目錄「全量」拉一次（catalog 約 30 列、ttl 300s）。
 * 分類 / 搜尋一律在前端做（authoring UX 要即時、無 flicker），且搜尋需比對
 * key + name_zh + **description**（後端 `?q` 只比對 key/name，涵蓋不足），故不帶 query。
 */
export const useDatasets = () => useEndpoint<DatasetCard[]>('/system/datasets', 300)
export const useAlertRules = () => useEndpoint<AlertRuleRow[]>('/system/alerts/rules', 300)
export const useAlertChannels = () => useEndpoint<AlertChannels>('/system/alerts/channels', 300)
export const useRiskSpec = () => useEndpoint<{ rules?: unknown[] }>('/system/risk/spec', 300)

/** Trigger an async ingest job; returns the job ref ({job_id,status}). */
export const useTriggerIngest = () =>
  useMutation({ mutationFn: (body: IngestBody) => triggerIngest(body) })

/**
 * Poll an ingest job's status until terminal (done/failed).
 * Unknown/expired id → 404 (A4 / doc 25 §5.2): the query enters the error state and
 * polling stops (else it would hammer a 404 forever); the page shows the error.
 */
export const useIngestStatus = (jobId: string | null) =>
  useQuery({
    queryKey: ['ingest-status', jobId],
    queryFn: () => getIngestStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (q) => {
      if (q.state.status === 'error') return false // 404/expired → stop polling
      const s = q.state.data?.data?.status
      return s === 'done' || s === 'failed' ? false : 1000
    },
  })

/** Trigger a survivorship-clean universe build (async job, ADR-032). */
export const useTriggerUniverseBuild = () =>
  useMutation({ mutationFn: (body: UniverseBuildBody) => triggerUniverseBuild(body) })

/**
 * Poll a universe-build job's status until terminal (done/failed).
 * Unknown/expired id → 404 (A4 / doc 25 §5.2): polling stops on the error state.
 */
export const useUniverseBuildStatus = (jobId: string | null) =>
  useQuery({
    queryKey: ['universe-build-status', jobId],
    queryFn: () => getUniverseBuildStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (q) => {
      if (q.state.status === 'error') return false // 404/expired → stop polling
      const s = q.state.data?.data?.status
      return s === 'done' || s === 'failed' ? false : 1000
    },
  })
