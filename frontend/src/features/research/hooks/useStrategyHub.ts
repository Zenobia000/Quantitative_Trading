/*
 * useStrategyHub — 策略中心（strategy hub）的聚合層。
 * 以「策略」為軸，把三個既有端點在 client 端 join（不需新後端）：
 *  - GET /strategies       → 策略型錄（name / title / description / config_schema）＝ roster 主源
 *  - GET /runs             → 判決帳本（append-only，newest-first）；依 run.strategy 分組
 *  - GET /monitor/watch    → Paper-Watch 艙位；依 watch.strategy 對齊
 * roster 由型錄驅動（策略軸），runs/watch 為 enrichment（缺席不阻塞清單）。
 */
import { useMemo } from 'react'
import { useStrategyRegistry } from './useStrategyRegistry'
import { useRuns } from './useRuns'
import { useWatchOverview } from '@/features/monitor/hooks/useWatch'
import type { StrategyInfo } from '../api/registry'
import type { RunRow } from '../api/runs'
import type { WatchRow } from '@/features/monitor/hooks/useWatch'

export interface StrategyHubRow {
  name: string
  title: string
  description: string
  runsCount: number
  /** 帳本 newest-first → 首列為最近一次 run（無 run 則 null）。 */
  latestRun: RunRow | null
  latestGateStatus: string | null
  /** 在觀察艙才有值。 */
  watch: WatchRow | null
}

export interface StrategyHubDetail {
  info: StrategyInfo | null
  name: string
  title: string
  /** 該策略的 runs，帳本序（newest-first），已去重。 */
  runs: RunRow[]
  latestRun: RunRow | null
  watch: WatchRow | null
}

/** 帳本 append-only → 同 run_id 可能重複（DOE re-run）；去重並保留帳本序（newest-first）。 */
function dedupeRuns(runs: RunRow[]): RunRow[] {
  const seen = new Set<string>()
  const out: RunRow[] = []
  for (const r of runs) {
    if (seen.has(r.run_id)) continue
    seen.add(r.run_id)
    out.push(r)
  }
  return out
}

/** 依 strategy name 分組去重後的 runs，保留組內帳本序。 */
function groupByStrategy(runs: RunRow[]): Map<string, RunRow[]> {
  const map = new Map<string, RunRow[]>()
  for (const r of runs) {
    const key = r.strategy ?? ''
    if (!key) continue
    const arr = map.get(key)
    if (arr) arr.push(r)
    else map.set(key, [r])
  }
  return map
}

/** 清單頁：型錄 × runs × watch → 每策略一列聚合視圖。 */
export function useStrategyHubList() {
  const registry = useStrategyRegistry()
  const runsQ = useRuns()
  const watchQ = useWatchOverview()

  const rows: StrategyHubRow[] = useMemo(() => {
    const infos = Array.isArray(registry.data?.data) ? registry.data.data : []
    const runsByStrat = groupByStrategy(dedupeRuns(runsQ.data?.data ?? []))
    const watchByStrat = new Map((watchQ.data?.data ?? []).map((w) => [w.strategy, w]))
    return infos.map((info) => {
      const stratRuns = runsByStrat.get(info.name) ?? []
      const latest = stratRuns[0] ?? null
      return {
        name: info.name,
        title: info.title,
        description: info.description,
        runsCount: stratRuns.length,
        latestRun: latest,
        latestGateStatus: latest?.gate_status ?? null,
        watch: watchByStrat.get(info.name) ?? null,
      }
    })
  }, [registry.data, runsQ.data, watchQ.data])

  return { registry, runsQ, watchQ, rows }
}

/** 詳情頁：單一策略的型錄資訊 + 判決時間線 + 觀察艙狀態。 */
export function useStrategyHubDetail(name: string | undefined) {
  const registry = useStrategyRegistry()
  const runsQ = useRuns()
  const watchQ = useWatchOverview()

  const detail: StrategyHubDetail = useMemo(() => {
    const infos = Array.isArray(registry.data?.data) ? registry.data.data : []
    const info = infos.find((i) => i.name === name) ?? null
    const stratRuns = name ? dedupeRuns(runsQ.data?.data ?? []).filter((r) => r.strategy === name) : []
    const watch = (watchQ.data?.data ?? []).find((w) => w.strategy === name) ?? null
    return {
      info,
      name: name ?? '',
      title: info?.title ?? name ?? '',
      runs: stratRuns,
      latestRun: stratRuns[0] ?? null,
      watch,
    }
  }, [registry.data, runsQ.data, watchQ.data, name])

  return { registry, runsQ, watchQ, detail }
}
