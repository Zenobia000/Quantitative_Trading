/* Home cockpit hooks。 */
import { useQuery } from '@tanstack/react-query'
import { getRecent, getResearchStatus } from '../api/home'
import { ttlToMs } from '@/services/queryClient'

export const useResearchStatus = () =>
  useQuery({ queryKey: ['home', 'research-status'], queryFn: getResearchStatus, staleTime: ttlToMs(300, 300) })

export const useRecent = () =>
  useQuery({ queryKey: ['home', 'recent'], queryFn: getRecent, staleTime: ttlToMs(300, 300) })
