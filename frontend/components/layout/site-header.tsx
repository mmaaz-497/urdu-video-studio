'use client'

import { Clapperboard, LogOut } from 'lucide-react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { ApiError, apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

export interface SiteHeaderProps {
  variant: 'authenticated' | 'anonymous'
}

const NAV_LINKS = [
  { href: '/create', label: 'Create' },
  { href: '/videos', label: 'My Videos' },
]

/** Pill tab; the active route is a raised slab. */
function navLinkClass(active: boolean) {
  return cn(
    'rounded-full border border-transparent px-4 py-1.5 text-body-sm font-medium text-muted-foreground transition-colors duration-150 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
    active && 'surface-3d border-border bg-surface-raised text-foreground shadow-depth-1'
  )
}

export function SiteHeader({ variant }: SiteHeaderProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await apiClient.post('/auth/logout')
      router.push('/login')
      router.refresh()
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Could not log out. Please try again.'
      toast.error(message)
    } finally {
      setLoggingOut(false)
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 shadow-[0_8px_24px_-16px_rgb(0_0_0/0.35)] backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          href={variant === 'authenticated' ? '/create' : '/'}
          className="flex items-center gap-2"
        >
          <span className="bg-accent-gradient flex h-8 w-8 items-center justify-center rounded-md shadow-cta">
            <Clapperboard className="h-4 w-4 text-white" />
          </span>
          <span className="text-h3 font-semibold">Urdu Video Studio</span>
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 sm:flex">
          {variant === 'authenticated' &&
            NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                aria-current={pathname?.startsWith(link.href) ? 'page' : undefined}
                className={navLinkClass(pathname?.startsWith(link.href) ?? false)}
              >
                {link.label}
              </Link>
            ))}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          {variant === 'authenticated' ? (
            <Button variant="ghost" size="sm" onClick={handleLogout} disabled={loggingOut}>
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </Button>
          ) : (
            <>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/login">Login</Link>
              </Button>
              <Button size="sm" variant="gradient" asChild>
                <Link href="/register">Start Creating</Link>
              </Button>
            </>
          )}
        </div>
      </div>

      {variant === 'authenticated' && (
        <nav
          aria-label="Main"
          className="flex items-center gap-1 border-t border-border px-3 pb-3 pt-2 sm:hidden"
        >
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname?.startsWith(link.href) ? 'page' : undefined}
              className={navLinkClass(pathname?.startsWith(link.href) ?? false)}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      )}
      <span
        aria-hidden
        className="hairline-gradient absolute inset-x-0 -bottom-px h-px opacity-70"
      />
    </header>
  )
}
