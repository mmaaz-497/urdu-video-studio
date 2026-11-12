'use client'

import { useEffect, useRef, type PointerEvent, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

export interface TiltProps {
  children: ReactNode
  className?: string
  /** Maximum rotation in degrees on each axis. Keep small — this is a hint of depth. */
  max?: number
  /** Adds a soft highlight that follows the pointer. */
  glare?: boolean
}

/** Subtle pointer-tracked perspective tilt. Only reacts to a mouse (touch gets
 * static depth) and does nothing under prefers-reduced-motion. A resting angle
 * can be set from CSS with `[--rx:…] [--ry:…]` classes; the pointer overrides
 * it and leaving restores it. */
export function Tilt({ children, className, max = 5, glare = false }: TiltProps) {
  const ref = useRef<HTMLDivElement | null>(null)
  const frame = useRef<number | null>(null)
  const reducedMotion = useRef(false)

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const sync = () => {
      reducedMotion.current = query.matches
    }
    sync()
    query.addEventListener('change', sync)
    return () => {
      query.removeEventListener('change', sync)
      if (frame.current !== null) cancelAnimationFrame(frame.current)
    }
  }, [])

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const el = ref.current
    if (!el || event.pointerType !== 'mouse' || reducedMotion.current) return
    const rect = el.getBoundingClientRect()
    const x = (event.clientX - rect.left) / rect.width
    const y = (event.clientY - rect.top) / rect.height
    if (frame.current !== null) cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      el.style.setProperty('--rx', `${((0.5 - y) * 2 * max).toFixed(2)}deg`)
      el.style.setProperty('--ry', `${((x - 0.5) * 2 * max).toFixed(2)}deg`)
      el.style.setProperty('--gx', `${(x * 100).toFixed(1)}%`)
      el.style.setProperty('--gy', `${(y * 100).toFixed(1)}%`)
      el.dataset.tilting = 'true'
    })
  }

  function handlePointerLeave() {
    const el = ref.current
    if (!el) return
    if (frame.current !== null) cancelAnimationFrame(frame.current)
    frame.current = null
    el.style.removeProperty('--rx')
    el.style.removeProperty('--ry')
    delete el.dataset.tilting
  }

  return (
    <div
      ref={ref}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      className={cn('tilt relative', className)}
    >
      {children}
      {glare && (
        <span
          aria-hidden
          className="tilt-glare pointer-events-none absolute inset-0 z-10 rounded-[inherit]"
        />
      )}
    </div>
  )
}
