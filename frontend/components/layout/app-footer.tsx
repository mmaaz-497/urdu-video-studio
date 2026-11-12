import { Clapperboard } from 'lucide-react'
import Link from 'next/link'

const FOOTER_LINKS = [
  { href: '/create', label: 'Create' },
  { href: '/videos', label: 'My Videos' },
]

/** Footer for the authenticated app shell. The marketing footer links to
 * landing-page anchors and login/sign-up, which make no sense once signed in. */
export function AppFooter() {
  return (
    <footer className="relative mt-16 border-t border-border bg-surface/40">
      <span aria-hidden className="hairline-gradient absolute inset-x-0 -top-px h-px" />
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-sm">
            <Link href="/create" className="flex w-fit items-center gap-2">
              <span className="bg-accent-gradient flex h-8 w-8 items-center justify-center rounded-md shadow-cta">
                <Clapperboard className="h-4 w-4 text-white" />
              </span>
              <span className="text-h3 font-semibold">Urdu Video Studio</span>
            </Link>
            <p className="mt-3 text-body-sm text-muted-foreground">
              Short educational videos with Urdu narration, made from a single idea.
            </p>
          </div>

          <nav aria-label="Footer" className="flex flex-wrap gap-2">
            {FOOTER_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-full border border-border bg-surface px-4 py-1.5 text-body-sm font-medium text-muted-foreground shadow-depth-1 transition-colors duration-150 hover:border-primary/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="mt-8 flex flex-col gap-2 border-t border-border pt-6 text-body-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Urdu Video Studio. For educational use.</p>
          <p className="urdu text-body-sm" dir="rtl" lang="ur" style={{ lineHeight: 2 }}>
            آپ کا خیال، آپ کی اردو ویڈیو
          </p>
        </div>
      </div>
    </footer>
  )
}
