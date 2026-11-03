import type { ReactNode } from 'react'

import { SiteHeader } from '@/components/layout/site-header'

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteHeader variant="authenticated" />
      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">{children}</main>
    </>
  )
}
