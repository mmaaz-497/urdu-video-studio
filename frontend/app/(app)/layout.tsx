import type { ReactNode } from 'react'

import { AppFooter } from '@/components/layout/app-footer'
import { SiteHeader } from '@/components/layout/site-header'

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader variant="authenticated" />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>
      <AppFooter />
    </div>
  )
}
