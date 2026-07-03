/* useRunCandles — 個股 K 線 + 進出場 marker（GET /runs/{id}/candles，後端 S4）。 */
import { useQuery } from '@tanstack/react-query'
import { getRunCandles } from '../api/candles'
import { ttlToMs } from '@/services/queryClient'

/**
 * @param runId run id（缺省時 disabled）
 * @param stockId 指定個股 stock_id；缺省 → 後端選清單第一檔（回應含 stock_ids 供 selector）
 */
export function useRunCandles(runId: string | undefined, stockId?: string) {
  return useQuery({
    queryKey: ['run-candles', runId, stockId ?? null],
    queryFn: () => getRunCandles(runId as string, stockId),
    enabled: !!runId,
    staleTime: (q) => ttlToMs(q.state.data?.meta?.ttl, 300),
  })
}
