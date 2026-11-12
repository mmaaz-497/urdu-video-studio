import { FileCheck2, PenLine, Sparkles } from 'lucide-react'

import { Reveal } from '@/components/marketing/reveal'
import { Tilt } from '@/components/ui/tilt'

const STEPS = [
  {
    icon: PenLine,
    title: 'Write your idea',
    body: 'Describe what you want to teach in Roman Urdu or Urdu — one or two sentences is enough.',
    sample: (
      <p className="rounded-sm border border-border bg-background/60 p-3 text-body-sm text-muted-foreground">
        “bachon ko bottles se solar heater banana sikhao”
      </p>
    ),
  },
  {
    icon: FileCheck2,
    title: 'Review the script',
    body: 'We draft a clean Urdu narration. Read it, tweak the wording, and approve it before anything is generated.',
    sample: (
      <p
        className="urdu rounded-sm border border-border bg-background/60 p-3 text-urdu-script"
        dir="rtl"
        lang="ur"
      >
        آج ہم پلاسٹک کی بوتلوں سے پانی گرم کرنا سیکھیں گے۔
      </p>
    ),
  },
  {
    icon: Sparkles,
    title: 'Get your video',
    body: 'Watch each step as your scenes and voice-over come together, then play or download the finished video.',
    sample: (
      <div className="relative aspect-video overflow-hidden rounded-sm border border-border bg-black">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/samples/sample-3.jpg" alt="" className="h-full w-full object-cover" loading="lazy" />
        <span className="absolute bottom-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-body-sm font-medium text-success backdrop-blur">
          Ready
        </span>
      </div>
    ),
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 border-y border-border bg-surface/40">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <Reveal className="max-w-2xl">
          <p className="text-body-sm font-semibold uppercase tracking-wider text-primary">How it works</p>
          <h2 className="mt-2 text-h1 font-bold tracking-tight">From a sentence to a finished video in three steps</h2>
        </Reveal>

        <ol className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="min-w-0">
              <Reveal delay={i * 100} className="h-full">
                <Tilt max={7} glare className="h-full rounded-md">
                <div className="surface-3d lift relative flex h-full flex-col gap-4 overflow-hidden rounded-md border border-border bg-surface p-6 shadow-depth-2">
                  <span
                    aria-hidden
                    className="absolute -right-2 -top-4 text-[6rem] font-bold leading-none text-accent-gradient opacity-20"
                  >
                    {i + 1}
                  </span>
                  <span className="bg-accent-gradient flex h-10 w-10 items-center justify-center rounded-sm shadow-cta">
                    <step.icon className="h-5 w-5 text-white" />
                  </span>
                  <h3 className="text-h3 font-semibold">
                    <span className="sr-only">Step {i + 1}: </span>
                    {step.title}
                  </h3>
                  <p className="text-body text-muted-foreground">{step.body}</p>
                  <div className="mt-auto pt-2">{step.sample}</div>
                </div>
                </Tilt>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
