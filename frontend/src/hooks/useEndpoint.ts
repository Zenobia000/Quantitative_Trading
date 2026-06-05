/* 通用 typed 端點 hook — 呼叫真實後端端點，回 ApiResult。 */
import { useQuery } from '@tanstack/react-query'
import { http } from '@/services/http'
import type { ApiResult } from '@/types/domain'

export function useEndpoint<T = unknown>(path: string | null, ttlSec = 60) {
  return useQuery<ApiResult<T>>({
    queryKey: ['endpoint', path],
    queryFn: () => http<T>(path as string),
    enabled: !!path,
    staleTime: ttlSec * 1000,
  })
}
