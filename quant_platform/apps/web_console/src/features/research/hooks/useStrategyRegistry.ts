/* useStrategyRegistry — 策略型錄（GET /strategies，shipped，ADR-028）。 */
import { useQuery } from '@tanstack/react-query'
import { getStrategyAsset, getStrategyOptimizationSchema, listStrategyRegistry } from '../api/registry'

export function useStrategyRegistry() {
  return useQuery({
    queryKey: ['strategy-registry'],
    queryFn: listStrategyRegistry,
    staleTime: 10 * 60_000, // 型錄低頻變動
  })
}

export function useStrategyAsset(strategy: string | undefined) {
  return useQuery({
    queryKey: ['strategy-asset', strategy],
    queryFn: () => getStrategyAsset(strategy as string),
    enabled: !!strategy,
    staleTime: 10 * 60_000,
  })
}

export function useStrategyOptimizationSchema(strategy: string | undefined) {
  return useQuery({
    queryKey: ['strategy-optimization-schema', strategy],
    queryFn: () => getStrategyOptimizationSchema(strategy as string),
    enabled: !!strategy,
    staleTime: 10 * 60_000,
  })
}
