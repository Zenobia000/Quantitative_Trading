/* useGateSpec — IS gate 硬門檻（GET /gate/spec，shipped）。 */
import { useQuery } from '@tanstack/react-query'
import { getGateSpec } from '../api/gate'

export function useGateSpec() {
  return useQuery({
    queryKey: ['gate-spec'],
    queryFn: getGateSpec,
    staleTime: 10 * 60_000, // 規格低頻變動
  })
}
