/* useRunCandles — 個股 K 線 + 進出場 marker（GET /runs/{id}/candles，後端 S4）。 */
import { useQuery } from '@tanstack/react-query'
import { getRunCandles } from '../api/candles'
import { ttlToMs } from '@/services/queryClient'

/**
 * @param runId run id（缺省時 disabled）
 * @param symbol 指定個股；缺省 → 後端選貢獻/清單第一檔（回應含 symbols 供 selector）
 */
export function useRunCandles(runId: string | undefined, symbol?: string) {
  return useQuery({
    queryKey: ['run-candles', runId, symbol ?? null],
    queryFn: () => getRunCandles(runId as string, symbol),
    enabled: !!runId,
    staleTime: ttlToMs(300, 300),
  })
}
