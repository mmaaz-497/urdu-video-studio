import Link from 'next/link'
import type { ReactNode } from 'react'

import { ThemeToggle } from '@/components/layout/theme-toggle'

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[480px] bg-accent-gradient opacity-20 blur-3xl"
      />

      <header className="relative z-10 flex items-center justify-between px-4 py-6 sm:px-6">
        <Link href="/" className="text-h3 font-semibold">
          Urdu Video Studio
        </Link>
        <ThemeToggle />
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-8 sm:px-6">
        {children}
      </main>
    </div>
  )
}
