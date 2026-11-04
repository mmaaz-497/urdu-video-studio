import { useQuery } from '@tanstack/react-query'

import { apiClient } from '@/lib/api-client'
import type { StudentProfile } from '@/lib/types'

/** Shared `GET /me` usage query — backs the usage badge on Create and the
 * limit-reached guard on both Create (Generate) and Review (Approve). */
export function useUsage() {
  return useQuery<StudentProfile>({
    queryKey: ['me'],
    queryFn: () => apiClient.get<StudentProfile>('/me'),
  })
}

export function formatResetTime(resetsAt: string): string {
  return new Date(resetsAt).toLocaleString('en-US', {
    timeZone: 'Asia/Karachi',
    hour: 'numeric',
    minute: '2-digit',
    month: 'short',
    day: 'numeric',
  })
}
