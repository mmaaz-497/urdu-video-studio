'use client'

import { Clock } from 'lucide-react'

import { cn } from '@/lib/utils'
import { formatResetTime, useUsage } from '@/lib/use-usage'

export interface UsageBadgeProps {
  className?: string
}

/** "X of Y videos left today" pill (design-system.md), reading `GET /me`'s
 * usage summary. Switches to warning styling once the daily limit is
 * reached and shows the Asia/Karachi midnight reset time. */
export function UsageBadge({ className }: UsageBadgeProps) {
  const { data, isLoading } = useUsage()

  if (isLoading || !data) return null

  const left = Math.max(0, data.usage.videoLimit - data.usage.videosUsedToday)
  const reached = left === 0

  return (
    <span
      role="status"
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-body-sm font-medium tabular-nums',
        reached
          ? 'border-warning/40 bg-warning/10 text-warning'
          : 'border-border bg-surface text-muted-foreground',
        className
      )}
    >
      {reached ? <Clock className="h-3.5 w-3.5" /> : null}
      {left} of {data.usage.videoLimit} videos left today
      {reached && <span className="font-normal">— resets {formatResetTime(data.usage.resetsAt)}</span>}
    </span>
  )
}
