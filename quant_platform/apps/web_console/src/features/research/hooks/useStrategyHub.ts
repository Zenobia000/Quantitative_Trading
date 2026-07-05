/*
 * useStrategyHub — 策略資產工作台（strategy asset）的聚合層（Goal 7）。
 * 以「策略」為軸，把四個既有端點在 client 端 join（不需新後端）：
 *  - GET /strategies         → 策略型錄（name / title / description=機制 / config_schema）＝ roster 主源
 *  - GET /runs               → 判決帳本（append-only，newest-first）；依 run.strategy 分組
 *  - GET /monitor/watch      → Paper-Watch 艙位；依 watch.strategy 對齊
 *  - GET /research/candidates → 候選池（#188 真後端）；依 candidate.strategy 對齊（假設/state/五維/next_action）
 * roster 由型錄驅動（策略軸），runs/watch/candidate 為 enrichment（缺席不阻塞清單）。
 */
import { useMemo } from 'react'
import { useStrategyRegistry } from './useStrategyRegistry'
import { useRuns } from './useRuns'
import { useStrategyCandidates, candidatesByStrategy } from './useStrategyCandidate'
import { useWatchOverview } from '@/features/monitor/hooks/useWatch'
import type { StrategyInfo } from '../api/registry'
import type { RunRow } from '../api/runs'
import type { Candidate } from '../api/candidates'
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
  /** 候選池對齊（最新一筆；不在池中則 null）——假設/state/五維燈/profile 來源。 */
  candidate: Candidate | null
  /**
   * 卡片一行假設：候選假設 → 最近 run 假設 → 型錄機制描述 → null。
   * （fallback 鏈由高保真到低保真，讓卡在候選未落地時仍有可讀命題。）
   */
  hypothesis: string | null
}

export interface StrategyHubDetail {
  info: StrategyInfo | null
  name: string
  title: string
  /** 該策略的 runs，帳本序（newest-first），已去重。 */
  runs: RunRow[]
  latestRun: RunRow | null
  watch: WatchRow | null
  /** 候選池對齊（最新一筆；不在池中則 null）——候選生命週期 section 資料源。 */
  candidate: Candidate | null
  /** 假設：候選假設 → 最近 run 假設 → null（型錄 description 另作「機制」，不混入假設）。 */
  hypothesis: string | null
  /** 機制：型錄 description（authoring 字典的策略機制說明）。 */
  mechanism: string | null
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

/** 卡片一行假設 fallback 鏈（候選 → 最近 run → 型錄機制 → null）。 */
function listHypothesis(candidate: Candidate | null, latestRun: RunRow | null, description: string): string | null {
  return candidate?.hypothesis || latestRun?.hypothesis || description || null
}

/** 清單頁：型錄 × runs × watch × candidates → 每策略一列研究資產視圖。 */
export function useStrategyHubList() {
  const registry = useStrategyRegistry()
  const runsQ = useRuns()
  const watchQ = useWatchOverview()
  const candidatesQ = useStrategyCandidates()

  const rows: StrategyHubRow[] = useMemo(() => {
    const infos = Array.isArray(registry.data?.data) ? registry.data.data : []
    const runsByStrat = groupByStrategy(dedupeRuns(runsQ.data?.data ?? []))
    const watchByStrat = new Map((watchQ.data?.data ?? []).map((w) => [w.strategy, w]))
    const candByStrat = candidatesByStrategy(candidatesQ.data)
    return infos.map((info) => {
      const stratRuns = runsByStrat.get(info.name) ?? []
      const latest = stratRuns[0] ?? null
      const candidate = candByStrat.get(info.name) ?? null
      return {
        name: info.name,
        title: info.title,
        description: info.description,
        runsCount: stratRuns.length,
        latestRun: latest,
        latestGateStatus: latest?.gate_status ?? null,
        watch: watchByStrat.get(info.name) ?? null,
        candidate,
        hypothesis: listHypothesis(candidate, latest, info.description),
      }
    })
  }, [registry.data, runsQ.data, watchQ.data, candidatesQ.data])

  return { registry, runsQ, watchQ, candidatesQ, rows }
}

/** 詳情頁：單一策略的型錄資訊 + 假設/機制 + 候選生命週期 + 判決時間線 + 觀察艙狀態。 */
export function useStrategyHubDetail(name: string | undefined) {
  const registry = useStrategyRegistry()
  const runsQ = useRuns()
  const watchQ = useWatchOverview()
  const candidatesQ = useStrategyCandidates()

  const detail: StrategyHubDetail = useMemo(() => {
    const infos = Array.isArray(registry.data?.data) ? registry.data.data : []
    const info = infos.find((i) => i.name === name) ?? null
    const stratRuns = name ? dedupeRuns(runsQ.data?.data ?? []).filter((r) => r.strategy === name) : []
    const latest = stratRuns[0] ?? null
    const candidate = name ? candidatesByStrategy(candidatesQ.data).get(name) ?? null : null
    return {
      info,
      name: name ?? '',
      title: info?.title ?? name ?? '',
      runs: stratRuns,
      latestRun: latest,
      watch: (watchQ.data?.data ?? []).find((w) => w.strategy === name) ?? null,
      candidate,
      hypothesis: candidate?.hypothesis || latest?.hypothesis || null,
      mechanism: info?.description || null,
    }
  }, [registry.data, runsQ.data, watchQ.data, candidatesQ.data, name])

  return { registry, runsQ, watchQ, candidatesQ, detail }
}
