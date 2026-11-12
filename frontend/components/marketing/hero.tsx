'use client'

import { ArrowRight, CheckCircle2, Pause, Play } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Tilt } from '@/components/ui/tilt'

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
        {/* Perspective floor — a grid receding to the horizon */}
        <div className="floor-3d absolute inset-x-0 bottom-0 h-[60%]">
          <span />
        </div>
        {/* Solid spheres at different depths */}
        <div className="orb-3d absolute left-[4%] top-[14%] hidden h-14 w-14 animate-float motion-reduce:animate-none md:block" />
        <div
          className="orb-3d absolute bottom-[12%] left-[44%] hidden h-8 w-8 animate-float [--orb:var(--gradient-to)] motion-reduce:animate-none md:block"
          style={{ animationDelay: '-3s' }}
        />
      </div>

      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-14 sm:px-6 md:pt-20 lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:pb-20">
        <div className="min-w-0">
          <p className="mb-5 inline-flex animate-fade-up items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1 text-body-sm text-muted-foreground shadow-depth-1 backdrop-blur">
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
            <Button size="lg" variant="gradient" asChild>
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
          {/* Ground glow — the frame appears to hover above the page */}
          <div
            aria-hidden
            className="absolute inset-x-10 -bottom-4 h-12 rounded-[50%] bg-[var(--gradient-from)] opacity-30 blur-2xl"
          />
          {/* Resting angle on desktop; the pointer straightens/steers it */}
          <Tilt
            max={10}
            glare
            className="tilt-3d rounded-lg [--rx:4deg] [--ry:-8deg] lg:[--rx:7deg] lg:[--ry:-16deg]"
          >
            {/* Stacked sheets behind the frame, each further back */}
            <div
              aria-hidden
              className="absolute inset-0 rounded-lg border border-border bg-surface-raised opacity-60 [transform:translate3d(28px,28px,-90px)]"
            />
            <div
              aria-hidden
              className="absolute inset-0 rounded-lg border border-border bg-surface-raised opacity-80 [transform:translate3d(14px,14px,-45px)]"
            />
            <div
              aria-hidden
              className="bg-accent-gradient absolute -inset-px rounded-lg opacity-70 blur-sm"
            />
            <div className="relative overflow-hidden rounded-lg border border-border bg-black shadow-depth-3">
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

            {/* Status chip floating in front of the frame */}
            <div
              aria-hidden
              className="absolute -left-4 top-6 hidden [transform:translateZ(70px)] sm:block lg:-left-10"
            >
              <div className="surface-3d flex animate-float items-center gap-2 rounded-full border border-border bg-surface-raised px-3 py-1.5 text-body-sm font-medium shadow-depth-2 motion-reduce:animate-none">
                <CheckCircle2 className="h-4 w-4 text-success" />
                Script approved
              </div>
            </div>
            <div
              aria-hidden
              className="orb-3d absolute -right-5 -top-5 hidden h-12 w-12 [--orb:var(--gradient-to)] [transform:translateZ(90px)] sm:block"
            />

            {/* Narration caption chip — sample Urdu renders RTL */}
            <div className="relative z-20 -mt-6 ml-auto mr-3 w-fit max-w-[88%] [transform:translateZ(60px)] sm:-mt-8 sm:mr-6">
              <div
                className="surface-3d animate-float rounded-md border border-border bg-surface-raised px-4 py-2 shadow-depth-3 motion-reduce:animate-none"
                style={{ animationDelay: '-2s' }}
              >
                <p className="mb-0.5 text-body-sm font-medium uppercase tracking-wider text-muted-foreground">
                  Narration
                </p>
                <p className="urdu text-urdu-script" dir="rtl" lang="ur">
                  بچے بوتلوں سے سورج کی توانائی پکڑتے ہیں۔
                </p>
              </div>
            </div>
          </Tilt>
        </div>
      </div>
    </section>
  )
}
