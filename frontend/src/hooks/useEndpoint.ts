/* 通用 typed 端點 hook — 呼叫真實後端端點，回 ApiResult。 */
import { useQuery } from '@tanstack/react-query'
import { http } from '@/services/http'
import { ttlToMs } from '@/services/queryClient'
import type { ApiResult } from '@/types/domain'

/**
 * @param path  後端裸根路徑（null → disabled）
 * @param ttlSec 後端未回 `meta.ttl` 時的 fallback staleTime（秒）
 *
 * `staleTime` 由回應的 `meta.ttl` 驅動（doc 25 §5.1 / A2）：後端每端點宣告自己的
 * 建議快取秒數（5/30/60/300/600），前端不再各自硬編。fallback 用呼叫端傳入的 `ttlSec`。
 */
export function useEndpoint<T = unknown>(path: string | null, ttlSec = 60) {
  return useQuery<ApiResult<T>>({
    queryKey: ['endpoint', path],
    queryFn: () => http<T>(path as string),
    enabled: !!path,
    staleTime: (q) => ttlToMs((q.state.data as ApiResult<T> | undefined)?.meta?.ttl, ttlSec),
  })
}
