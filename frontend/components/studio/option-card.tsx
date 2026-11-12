'use client'

import { Check } from 'lucide-react'
import type { KeyboardEvent, ReactNode } from 'react'

import { cn } from '@/lib/utils'

export interface OptionCardProps {
  selected: boolean
  onSelect: () => void
  label: string
  sublabel?: string
  icon?: ReactNode
  /** Extra interactive control (e.g. a voice preview button) rendered in the
   * top-right corner. Callers must stop propagation on its own click handler
   * so it doesn't also trigger `onSelect`. */
  action?: ReactNode
  disabled?: boolean
  className?: string
  children?: ReactNode
}

/** Shared selectable card for the duration / aspect-ratio / voice groups on
 * the Create page (design-system.md "Option Card"). A `div` with
 * `role="radio"` rather than a native `<button>` so an optional nested
 * `action` control (e.g. a preview play button) stays valid HTML. */
export function OptionCard({
  selected,
  onSelect,
  label,
  sublabel,
  icon,
  action,
  disabled,
  className,
  children,
}: OptionCardProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (disabled) return
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect()
    }
  }

  return (
    <div
      role="radio"
      aria-checked={selected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={disabled ? undefined : onSelect}
      onKeyDown={handleKeyDown}
      className={cn(
        'relative flex min-w-[8.5rem] flex-1 shrink-0 cursor-pointer select-none snap-start flex-col items-center gap-2 rounded-md border border-border bg-surface p-4 text-center shadow-depth-1 transition-all duration-150',
        'hover:-translate-y-1 hover:border-primary/50 hover:bg-surface-raised active:translate-y-0.5 motion-reduce:transform-none',
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
        disabled && 'pointer-events-none cursor-not-allowed opacity-50',
        selected &&
          'surface-3d -translate-y-0.5 border-primary bg-surface-raised shadow-depth-2 ring-1 ring-primary/40',
        className
      )}
    >
      {selected && (
        <>
          <span aria-hidden className="hairline-gradient absolute inset-x-3 top-0 h-px" />
          <span
            aria-hidden
            className="bg-accent-gradient absolute left-2 top-2 flex h-5 w-5 items-center justify-center rounded-full shadow-[inset_0_1px_0_rgb(255_255_255/0.35)]"
          >
            <Check className="h-3 w-3 text-white" strokeWidth={3} />
          </span>
        </>
      )}
      {action && <div className="absolute right-2 top-2">{action}</div>}
      {icon && (
        <span
          className={cn(
            'flex h-9 items-center justify-center text-muted-foreground transition-colors duration-150',
            selected && 'text-primary'
          )}
        >
          {icon}
        </span>
      )}
      {children}
      <span className="text-body font-medium leading-tight">{label}</span>
      {sublabel && <span className="text-body-sm text-muted-foreground">{sublabel}</span>}
    </div>
  )
}

/** Proportional 16:9 / 9:16 shape shown inside an aspect-ratio OptionCard
 * instead of a generic icon (design-system.md Design Principle #3). */
export function AspectRatioShape({ ratio }: { ratio: '16:9' | '9:16' }) {
  return (
    <span
      aria-hidden
      className={cn(
        'rounded-sm border-2 border-current',
        ratio === '16:9' ? 'h-7 w-12' : 'h-12 w-7'
      )}
    />
  )
}
