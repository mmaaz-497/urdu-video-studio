import { cn } from '@/lib/utils'

export interface WordCounterProps {
  count: number
  limit: number
  className?: string
}

/** Live word-counter badge for the Review screen; switches to destructive
 * styling once over the target (FR-010) — callers disable "Approve & Create
 * Video" using the same `count > limit` comparison. */
export function WordCounter({ count, limit, className }: WordCounterProps) {
  const over = count > limit

  return (
    <span
      role="status"
      aria-live="polite"
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-body-sm font-medium tabular-nums',
        over
          ? 'border-destructive/40 bg-destructive/10 text-destructive'
          : 'border-border bg-surface text-muted-foreground',
        className
      )}
    >
      {count} / {limit} words
      {over && <span className="font-normal">— shorten to approve</span>}
    </span>
  )
}
