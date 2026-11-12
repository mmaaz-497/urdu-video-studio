import Link from 'next/link'
import type { ReactNode } from 'react'

import { ThemeToggle } from '@/components/layout/theme-toggle'
import { Tilt } from '@/components/ui/tilt'

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[480px] bg-accent-gradient opacity-20 blur-3xl"
      />
      {/* Second, nearer light source so the card sits between two depths */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -bottom-32 -right-24 h-80 w-80 animate-drift rounded-full bg-[var(--gradient-to)] opacity-15 blur-[100px] motion-reduce:animate-none" />
      </div>

      {/* Perspective floor and spheres give the card a space to sit in */}
      <div aria-hidden className="floor-3d pointer-events-none absolute inset-x-0 bottom-0 h-[55%]">
        <span />
      </div>
      <div
        aria-hidden
        className="orb-3d pointer-events-none absolute left-[12%] top-[26%] hidden h-16 w-16 animate-float motion-reduce:animate-none md:block"
      />
      <div
        aria-hidden
        className="orb-3d pointer-events-none absolute bottom-[22%] right-[14%] hidden h-10 w-10 animate-float [--orb:var(--gradient-to)] motion-reduce:animate-none md:block"
        style={{ animationDelay: '-3s' }}
      />

      <header className="relative z-10 flex items-center justify-between px-4 py-6 sm:px-6">
        <Link href="/" className="text-h3 font-semibold">
          Urdu Video Studio
        </Link>
        <ThemeToggle />
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-8 sm:px-6">
        <Tilt max={6} glare className="w-full max-w-md rounded-xl">
          {children}
        </Tilt>
      </main>
    </div>
  )
}
