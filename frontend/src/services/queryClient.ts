/*
 * TanStack Query client。realtime 用 polling + meta.ttl（doc 25 §5），不用 SSE。
 * 各 hook 可用 ttlToMs(meta.ttl) 覆寫 staleTime/refetchInterval。
 */
import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './http'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (count, err) => {
        // 4xx 不重試（驗證/鎖定/找不到），其餘最多 2 次
        if (err instanceof ApiError && err.status && err.status >= 400 && err.status < 500) return false
        return count < 2
      },
    },
  },
})

/** meta.ttl（秒）→ 毫秒，供 hook 設 staleTime / refetchInterval */
export function ttlToMs(ttl: number | undefined, fallbackSec = 60): number {
  return (ttl ?? fallbackSec) * 1000
}
