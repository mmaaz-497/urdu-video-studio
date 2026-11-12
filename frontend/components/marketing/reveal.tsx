'use client'

import { useEffect, useRef, useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

/** Fades children up (with a slight forward tilt, so they rise into place)
 * when scrolled into view. Content is fully visible on the
 * server / without JS / with reduced motion; the hidden state is only applied
 * after mount for elements that start below the fold. */
export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [state, setState] = useState<'visible' | 'hidden' | 'shown'>('visible')

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    if (el.getBoundingClientRect().top < window.innerHeight) return
    setState('hidden')
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setState('shown')
          io.disconnect()
        }
      },
      { rootMargin: '0px 0px -10% 0px' }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      style={{ transitionDelay: state === 'shown' ? `${delay}ms` : undefined }}
      className={cn(
        'transition-all duration-400 ease-out',
        state === 'hidden' &&
          'opacity-0 [transform:perspective(1000px)_translateY(20px)_rotateX(6deg)]',
        className
      )}
    >
      {children}
    </div>
  )
}
