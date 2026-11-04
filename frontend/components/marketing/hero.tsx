'use client'

import { ArrowRight, Pause, Play } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'

/** Landing hero: headline + CTA beside an autoplaying muted sample loop.
 * Under prefers-reduced-motion the video stays on its poster until the
 * visitor presses play. */
export function Hero() {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    video.play().then(() => setPlaying(true)).catch(() => {})
  }, [])

  function toggle() {
    const video = videoRef.current
    if (!video) return
    if (video.paused) {
      video.play().then(() => setPlaying(true)).catch(() => {})
    } else {
      video.pause()
      setPlaying(false)
    }
  }

  return (
    <section className="relative isolate overflow-hidden">
      {/* Aurora backdrop */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -left-1/4 -top-1/3 h-[34rem] w-[34rem] rounded-full bg-[var(--gradient-from)] opacity-25 blur-[120px] animate-drift motion-reduce:animate-none" />
        <div
          className="absolute -right-1/4 top-1/4 h-[30rem] w-[30rem] rounded-full bg-[var(--gradient-to)] opacity-20 blur-[120px] animate-drift motion-reduce:animate-none"
          style={{ animationDelay: '-9s' }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(hsl(var(--border)/0.5)_1px,transparent_1px),linear-gradient(90deg,hsl(var(--border)/0.5)_1px,transparent_1px)] bg-[size:56px_56px] [mask-image:radial-gradient(ellipse_at_50%_30%,black,transparent_70%)]" />
      </div>

      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-14 sm:px-6 md:pt-20 lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:pb-20">
        <div className="min-w-0">
          <p className="mb-5 inline-flex animate-fade-up items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1 text-body-sm text-muted-foreground backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            Educational videos, narrated in Urdu
          </p>
          <h1
            className="animate-fade-up text-display font-bold tracking-tight md:text-[3.5rem] md:leading-[1.05]"
            style={{ animationDelay: '80ms' }}
          >
            Turn one idea into an <span className="text-accent-gradient">Urdu-narrated</span> video.
          </h1>
          <p
            className="mt-6 max-w-xl animate-fade-up text-body text-muted-foreground md:text-lg"
            style={{ animationDelay: '160ms' }}
          >
            Type your idea in Roman Urdu or Urdu. We write the script, you approve it, and a short
            video with a natural Urdu voice-over is ready in minutes.
          </p>
          <div
            className="mt-8 flex animate-fade-up flex-wrap items-center gap-3"
            style={{ animationDelay: '240ms' }}
          >
            <Button size="lg" className="bg-accent-gradient text-white shadow-raised hover:opacity-90" asChild>
              <Link href="/register">
                Start Creating
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="#how-it-works">See how it works</Link>
            </Button>
          </div>
          <p className="mt-5 animate-fade-up text-body-sm text-muted-foreground" style={{ animationDelay: '320ms' }}>
            5, 10 or 15 second videos · Free to try
          </p>
        </div>

        <div className="relative animate-fade-up" style={{ animationDelay: '200ms' }}>
          <div aria-hidden className="absolute -inset-px rounded-lg bg-accent-gradient opacity-70 blur-sm" />
          <div className="relative overflow-hidden rounded-lg border border-border bg-black shadow-raised">
            <div className="aspect-video">
              <video
                ref={videoRef}
                src="/samples/sample-1.mp4"
                poster="/samples/sample-1.jpg"
                muted
                loop
                playsInline
                preload="metadata"
                aria-label="Sample video: children building a solar water heater from plastic bottles"
                className="h-full w-full object-cover"
              />
            </div>
            <button
              type="button"
              onClick={toggle}
              aria-label={playing ? 'Pause sample video' : 'Play sample video'}
              className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full border border-white/20 bg-black/50 text-white backdrop-blur transition-colors hover:bg-black/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </button>
          </div>

          {/* Narration caption chip — sample Urdu renders RTL */}
          <div className="relative -mt-6 ml-auto mr-3 w-fit max-w-[88%] rounded-md border border-border bg-surface-raised/90 px-4 py-2 shadow-raised backdrop-blur sm:-mt-8 sm:mr-6">
            <p className="mb-0.5 text-body-sm font-medium uppercase tracking-wider text-muted-foreground">
              Narration
            </p>
            <p className="urdu text-urdu-script" dir="rtl" lang="ur">
              بچے بوتلوں سے سورج کی توانائی پکڑتے ہیں۔
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
