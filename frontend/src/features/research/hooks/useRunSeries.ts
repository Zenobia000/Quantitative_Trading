/* useRunEquity / useRunTrades — run computed series（後端 8.H.3 / S4）。 */
import { useQuery } from '@tanstack/react-query'
import { getRunEquity, getRunTrades } from '../api/series'
import { ttlToMs } from '@/services/queryClient'

export function useRunEquity(runId: string | undefined) {
  return useQuery({
    queryKey: ['run-equity', runId],
    queryFn: () => getRunEquity(runId as string),
    enabled: !!runId,
    staleTime: ttlToMs(300, 300),
  })
}

export function useRunTrades(runId: string | undefined) {
  return useQuery({
    queryKey: ['run-trades', runId],
    queryFn: () => getRunTrades(runId as string),
    enabled: !!runId,
    staleTime: ttlToMs(300, 300),
  })
}
