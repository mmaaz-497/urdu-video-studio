import { Clapperboard } from 'lucide-react'
import Link from 'next/link'

export function SiteFooter() {
  return (
    <footer className="relative isolate overflow-hidden border-t border-border bg-surface/40">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-gradient">
                <Clapperboard className="h-4 w-4 text-white" />
              </span>
              <span className="text-h3 font-semibold">Urdu Video Studio</span>
            </div>
            <p className="mt-3 text-body-sm text-muted-foreground">
              Short educational videos with Urdu narration, made from a single idea.
            </p>
          </div>

          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-12 gap-y-3 text-body-sm sm:gap-x-16">
            <Link href="#how-it-works" className="text-muted-foreground hover:text-foreground">
              How it works
            </Link>
            <Link href="/login" className="text-muted-foreground hover:text-foreground">
              Login
            </Link>
            <Link href="#showcase" className="text-muted-foreground hover:text-foreground">
              Showcase
            </Link>
            <Link href="/register" className="text-muted-foreground hover:text-foreground">
              Sign up
            </Link>
            <Link href="#faq" className="text-muted-foreground hover:text-foreground">
              FAQ
            </Link>
          </nav>
        </div>

        <div className="mt-10 flex flex-col gap-2 border-t border-border pt-6 text-body-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Urdu Video Studio. For educational use.</p>
          <p className="urdu text-body-sm" dir="rtl" lang="ur" style={{ lineHeight: 2 }}>
            آپ کا خیال، آپ کی اردو ویڈیو
          </p>
        </div>
      </div>
    </footer>
  )
}
