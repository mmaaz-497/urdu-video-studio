'use client'

import { Play } from 'lucide-react'
import { useRef } from 'react'

import { Reveal } from '@/components/marketing/reveal'
import { Tilt } from '@/components/ui/tilt'

const SAMPLES = [
  {
    id: 1,
    title: 'بوتلوں سے سولر ہیٹر',
    caption: 'Rooftop science with recycled bottles',
    duration: 5,
  },
  {
    id: 2,
    title: 'کلاس روم میں سائنس تجربہ',
    caption: 'A hands-on chemistry lesson',
    duration: 5,
  },
  {
    id: 3,
    title: 'پانی اور رنگوں کا تجربہ',
    caption: 'A simple liquids experiment',
    duration: 5,
  },
]

function ShowcaseCard({ sample }: { sample: (typeof SAMPLES)[number] }) {
  const videoRef = useRef<HTMLVideoElement | null>(null)

  function start() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    videoRef.current?.play().catch(() => {})
  }

  function stop() {
    const video = videoRef.current
    if (!video) return
    video.pause()
    video.currentTime = 0
  }

  return (
    <div
      onMouseEnter={start}
      onMouseLeave={stop}
      onFocus={start}
      onBlur={stop}
      tabIndex={0}
      className="surface-3d group flex h-full flex-col overflow-hidden rounded-md border border-border bg-surface shadow-depth-2 outline-none transition-[box-shadow,border-color] duration-250 hover:border-primary/60 hover:shadow-depth-3 focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="relative aspect-video bg-black">
        <video
          ref={videoRef}
          src={`/samples/sample-${sample.id}.mp4`}
          poster={`/samples/sample-${sample.id}.jpg`}
          muted
          loop
          playsInline
          preload="none"
          aria-label={sample.caption}
          className="h-full w-full object-cover"
        />
        <span className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/20 opacity-100 transition-opacity duration-250 group-hover:opacity-0 group-focus-visible:opacity-0 motion-reduce:transition-none">
          <span className="flex h-12 w-12 items-center justify-center rounded-full border border-white/30 bg-black/40 text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.25),0_8px_20px_-6px_rgb(0_0_0/0.6)] backdrop-blur">
            <Play className="h-5 w-5" />
          </span>
        </span>
      </div>
      <div className="flex flex-col gap-2 p-4">
        <h3 className="urdu truncate text-h3 font-semibold" dir="rtl" lang="ur" title={sample.title}>
          {sample.title}
        </h3>
        <p className="text-body-sm text-muted-foreground">
          {sample.caption} · {sample.duration}s · 16:9
        </p>
      </div>
    </div>
  )
}

export function ShowcaseGrid() {
  return (
    <section id="showcase" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6">
      <Reveal className="max-w-2xl">
        <p className="text-body-sm font-semibold uppercase tracking-wider text-primary">Showcase</p>
        <h2 className="mt-2 text-h1 font-bold tracking-tight">See what an idea can become</h2>
        <p className="mt-3 text-body text-muted-foreground">
          Hover over a video to preview it. Every clip starts from a single sentence.
        </p>
      </Reveal>
      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {SAMPLES.map((sample, i) => (
          <Reveal key={sample.id} delay={i * 100}>
            <Tilt max={8} glare className="h-full rounded-md">
              <ShowcaseCard sample={sample} />
            </Tilt>
          </Reveal>
        ))}
      </div>
    </section>
  )
}
