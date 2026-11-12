'use client'

import {
  ArrowRight,
  Check,
  Clock,
  FileText,
  Film,
  Loader2,
  Mic,
  Pause,
  PenLine,
  Play,
  Sparkles,
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import { IdeaTextarea, IDEA_MAX_LENGTH, IDEA_MIN_LENGTH } from '@/components/studio/idea-textarea'
import { AspectRatioShape, OptionCard } from '@/components/studio/option-card'
import { UsageBadge } from '@/components/studio/usage-badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Tilt } from '@/components/ui/tilt'
import { ApiError, apiClient } from '@/lib/api-client'
import { writeDraft, type ReviewDraft } from '@/lib/review-draft'
import { formatResetTime, useUsage } from '@/lib/use-usage'
import { cn } from '@/lib/utils'
import type { AspectRatio, DurationSeconds, GeneratedScript, Voice, VoiceId } from '@/lib/types'

const DURATIONS: DurationSeconds[] = [5, 10, 15]
const ASPECT_RATIOS: { value: AspectRatio; sublabel: string }[] = [
  { value: '16:9', sublabel: 'Landscape' },
  { value: '9:16', sublabel: 'Portrait' },
]

const FLOW_STEPS = [
  { label: 'Idea', icon: PenLine },
  { label: 'Review script', icon: FileText },
  { label: 'Video', icon: Film },
]
const EXAMPLE_IDEAS = [
  {
    label: 'Photosynthesis',
    idea: 'Photosynthesis is how plants make their own food from sunlight',
  },
  { label: 'Phases of the moon', idea: 'Why does the moon change its shape during the month?' },
  {
    label: 'Pani ka chakkar',
    idea: 'Pani ka chakkar kaise chalta hai — baarish kahan se aati hai?',
  },
]
const OPTION_ROW =
  '-mx-5 flex snap-x gap-3 overflow-x-auto px-5 pb-3 pt-2 sm:mx-0 sm:grid sm:overflow-visible sm:p-0'

/** Numbered slab holding one step of the form. Pass `htmlFor` when the title
 * should label a form control instead of being a plain heading. */
function Panel({
  step,
  title,
  hint,
  htmlFor,
  children,
}: {
  step: number
  title: string
  hint: string
  htmlFor?: string
  children: ReactNode
}) {
  return (
    <Card className="animate-rise-in p-5 sm:p-6" style={{ animationDelay: `${(step - 1) * 70}ms` }}>
      <div className="mb-4 flex items-center gap-3">
        <span
          aria-hidden
          className="bg-accent-gradient flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-body-sm font-bold text-white shadow-cta"
        >
          {step}
        </span>
        <div className="min-w-0">
          {htmlFor ? (
            <label htmlFor={htmlFor} className="block text-h3 font-semibold">
              {title}
            </label>
          ) : (
            <h2 className="text-h3 font-semibold">{title}</h2>
          )}
          <p className="text-body-sm text-muted-foreground">{hint}</p>
        </div>
      </div>
      {children}
    </Card>
  )
}

export default function CreatePage() {
  const router = useRouter()
  const [idea, setIdea] = useState('')
  const [duration, setDuration] = useState<DurationSeconds>(5)
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9')
  const [voiceId, setVoiceId] = useState<VoiceId>('female')
  const [voices, setVoices] = useState<Voice[]>([])
  const [voicesLoading, setVoicesLoading] = useState(true)
  const [playingVoice, setPlayingVoice] = useState<VoiceId | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const { data: profile } = useUsage()
  const limitReached = profile ? profile.usage.videosUsedToday >= profile.usage.videoLimit : false

  useEffect(() => {
    apiClient
      .get<Voice[]>('/voices')
      .then(setVoices)
      .catch(() => toast.error('Could not load voice previews.'))
      .finally(() => setVoicesLoading(false))
  }, [])

  useEffect(() => {
    const audio = audioRef
    return () => {
      audio.current?.pause()
    }
  }, [])

  function togglePreview(voice: Voice) {
    if (playingVoice === voice.id) {
      audioRef.current?.pause()
      setPlayingVoice(null)
      return
    }
    audioRef.current?.pause()
    const audio = new Audio(voice.previewUrl)
    audio.addEventListener('ended', () => setPlayingVoice(null))
    audioRef.current = audio
    audio.play().then(
      () => setPlayingVoice(voice.id),
      () => toast.error('Could not play the voice preview.')
    )
  }

  const ideaValid = idea.length >= IDEA_MIN_LENGTH && idea.length <= IDEA_MAX_LENGTH
  const canSubmit = ideaValid && !submitting && !limitReached
  const voiceLabel =
    voices.find((voice) => voice.id === voiceId)?.label ??
    (voiceId === 'female' ? 'Female' : 'Male')
  const ratioLabel = ASPECT_RATIOS.find((ratio) => ratio.value === aspectRatio)?.sublabel
  const ideaStatus = ideaValid
    ? `${idea.length} characters`
    : idea.length === 0
      ? 'Not written yet'
      : idea.length < IDEA_MIN_LENGTH
        ? `Needs ${IDEA_MIN_LENGTH}+ characters`
        : 'Too long'

  async function handleSubmit() {
    if (!canSubmit) return
    setSubmitting(true)
    const idempotencyKey = crypto.randomUUID()
    try {
      const script = await apiClient.post<GeneratedScript>('/scripts', {
        idempotencyKey,
        idea,
        durationSeconds: duration,
        aspectRatio,
        voiceId,
      })
      const draft: ReviewDraft = {
        idea,
        durationSeconds: duration,
        aspectRatio,
        voiceId,
        ...script,
      }
      writeDraft(draft)
      router.push('/review')
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Could not generate a script. Please try again.'
      toast.error(message)
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-8">
      <header className="relative isolate overflow-hidden rounded-lg border border-border bg-surface/60 px-5 py-8 shadow-depth-2 sm:px-8 sm:py-10">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -left-20 -top-24 h-72 w-72 animate-drift rounded-full bg-[var(--gradient-from)] opacity-25 blur-[90px] motion-reduce:animate-none" />
          <div
            className="absolute -bottom-24 right-0 h-72 w-72 animate-drift rounded-full bg-[var(--gradient-to)] opacity-20 blur-[90px] motion-reduce:animate-none"
            style={{ animationDelay: '-9s' }}
          />
          <div className="floor-3d absolute inset-x-0 bottom-0 h-[75%]">
            <span />
          </div>
          <div className="orb-3d absolute bottom-[20%] right-[7%] hidden h-12 w-12 animate-float motion-reduce:animate-none md:block" />
          <div
            className="orb-3d absolute right-[24%] top-[42%] hidden h-6 w-6 animate-float [--orb:var(--gradient-to)] motion-reduce:animate-none md:block"
            style={{ animationDelay: '-3s' }}
          />
        </div>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-xl">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1 text-body-sm text-muted-foreground shadow-depth-1 backdrop-blur">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              New video
            </p>
            <h1 className="text-display font-bold tracking-tight">
              Create a <span className="text-accent-gradient">video</span>
            </h1>
            <p className="mt-3 text-body text-muted-foreground">
              Describe your idea, pick a style, and we&apos;ll turn it into a short Urdu script to
              review.
            </p>
          </div>
          <UsageBadge />
        </div>

        <ol className="mt-8 flex flex-wrap items-center gap-x-2 gap-y-3 text-body-sm">
          {FLOW_STEPS.map(({ label, icon: Icon }, index) => (
            <li key={label} className="flex items-center gap-2">
              <span
                aria-current={index === 0 ? 'step' : undefined}
                className={cn(
                  'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-medium backdrop-blur',
                  index === 0
                    ? 'surface-3d border-primary/60 bg-surface-raised text-foreground shadow-depth-1'
                    : 'border-border bg-surface/60 text-muted-foreground'
                )}
              >
                <Icon className={cn('h-3.5 w-3.5', index === 0 && 'text-primary')} />
                <span className="tabular-nums">{index + 1}.</span>
                {label}
              </span>
              {index < FLOW_STEPS.length - 1 && (
                <span aria-hidden className="hidden h-px w-6 bg-border sm:block" />
              )}
            </li>
          ))}
        </ol>
      </header>

      {limitReached && profile && (
        <div className="flex items-start gap-3 rounded-md border border-warning/40 bg-warning/10 p-4 text-body text-warning shadow-depth-1">
          <Clock className="mt-0.5 h-5 w-5 shrink-0" />
          <p>
            You&apos;ve used all your videos for today. Come back after midnight (Asia/Karachi) —
            resets {formatResetTime(profile.usage.resetsAt)}.
          </p>
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
        <div className="min-w-0 space-y-6">
          <Panel
            step={1}
            title="Your idea"
            hint="One or two sentences about what the video should teach."
            htmlFor="idea"
          >
            <IdeaTextarea value={idea} onChange={setIdea} disabled={submitting} />
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-body-sm text-muted-foreground">Try an example:</span>
              {EXAMPLE_IDEAS.map((example) => (
                <button
                  key={example.label}
                  type="button"
                  disabled={submitting}
                  onClick={() => setIdea(example.idea)}
                  className="rounded-full border border-border bg-surface px-3 py-1 text-body-sm font-medium text-muted-foreground shadow-depth-1 transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring active:translate-y-0.5 disabled:pointer-events-none disabled:opacity-50 motion-reduce:transform-none"
                >
                  {example.label}
                </button>
              ))}
            </div>
          </Panel>

          <Panel step={2} title="Duration" hint="How long the finished video runs.">
            <div
              role="radiogroup"
              aria-label="Duration"
              className={cn(OPTION_ROW, 'sm:grid-cols-3')}
            >
              {DURATIONS.map((value) => (
                <OptionCard
                  key={value}
                  selected={duration === value}
                  onSelect={() => setDuration(value)}
                  disabled={submitting}
                  label={`${value}s`}
                  className="min-w-0"
                  icon={<Clock className="h-6 w-6" />}
                />
              ))}
            </div>
          </Panel>

          <Panel step={3} title="Aspect ratio" hint="Landscape for screens, portrait for phones.">
            <div
              role="radiogroup"
              aria-label="Aspect ratio"
              className={cn(OPTION_ROW, 'sm:grid-cols-2')}
            >
              {ASPECT_RATIOS.map(({ value, sublabel }) => (
                <OptionCard
                  key={value}
                  selected={aspectRatio === value}
                  onSelect={() => setAspectRatio(value)}
                  disabled={submitting}
                  label={value}
                  sublabel={sublabel}
                >
                  <AspectRatioShape ratio={value} />
                </OptionCard>
              ))}
            </div>
          </Panel>

          <Panel step={4} title="Voice" hint="Press play to hear a sample of each narrator.">
            <div role="radiogroup" aria-label="Voice" className={cn(OPTION_ROW, 'sm:grid-cols-2')}>
              {voicesLoading &&
                [0, 1].map((key) => (
                  <div
                    key={key}
                    aria-hidden
                    className="h-28 min-w-[8.5rem] flex-1 animate-pulse rounded-md border border-border bg-surface shadow-depth-1 motion-reduce:animate-none"
                  />
                ))}
              {!voicesLoading && voices.length === 0 && (
                <p className="text-body-sm text-muted-foreground sm:col-span-2">
                  Could not load the voices. Refresh the page to try again.
                </p>
              )}
              {voices.map((voice) => (
                <OptionCard
                  key={voice.id}
                  selected={voiceId === voice.id}
                  onSelect={() => setVoiceId(voice.id)}
                  disabled={submitting}
                  label={voice.label}
                  icon={<Mic className="h-6 w-6" />}
                  action={
                    <button
                      type="button"
                      aria-label={
                        playingVoice === voice.id
                          ? `Pause ${voice.label} preview`
                          : `Play ${voice.label} preview`
                      }
                      onClick={(event) => {
                        event.stopPropagation()
                        togglePreview(voice)
                      }}
                      className={cn(
                        'flex h-7 w-7 items-center justify-center rounded-full border border-border bg-background/80 text-foreground transition-colors hover:border-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                        playingVoice === voice.id && 'border-primary text-primary'
                      )}
                    >
                      {playingVoice === voice.id ? (
                        <Pause className="h-3.5 w-3.5" />
                      ) : (
                        <Play className="h-3.5 w-3.5" />
                      )}
                    </button>
                  }
                />
              ))}
            </div>
          </Panel>
        </div>

        <aside className="lg:sticky lg:top-24">
          <Card className="animate-rise-in p-5 sm:p-6" style={{ animationDelay: '280ms' }}>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-h3 font-semibold">Your video</h2>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-0.5 text-body-sm text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                Live preview
              </span>
            </div>

            {/* Mock frame that takes the shape of the chosen aspect ratio */}
            <div aria-hidden className="relative mt-5 flex h-60 items-center justify-center">
              <div className="absolute inset-x-12 bottom-3 h-10 rounded-[50%] bg-[var(--gradient-from)] opacity-30 blur-2xl" />
              <Tilt max={10} glare className="tilt-3d rounded-md [--rx:6deg] [--ry:-14deg]">
                <div
                  className={cn(
                    'relative transition-[width,height] duration-400 ease-out [transform-style:preserve-3d]',
                    aspectRatio === '16:9' ? 'h-[7.875rem] w-56' : 'h-48 w-[6.75rem]'
                  )}
                >
                  <div className="absolute inset-0 rounded-md border border-border bg-surface-raised opacity-60 [transform:translate3d(16px,16px,-60px)]" />
                  <div className="absolute inset-0 rounded-md border border-border bg-surface-raised opacity-80 [transform:translate3d(8px,8px,-30px)]" />
                  <div className="bg-accent-gradient absolute -inset-px rounded-md opacity-70 blur-sm" />
                  <div className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-md border border-border bg-[#0b0a1c] shadow-depth-3">
                    <div className="bg-accent-gradient absolute inset-0 opacity-25" />
                    <span className="relative flex h-10 w-10 items-center justify-center rounded-full border border-white/25 bg-white/10 text-white backdrop-blur">
                      <Play className="h-4 w-4 translate-x-px" />
                    </span>
                    <div className="absolute inset-x-3 bottom-3 h-1 overflow-hidden rounded-full bg-white/20">
                      <div className="bg-accent-gradient h-full w-1/3 rounded-full" />
                    </div>
                  </div>
                  <div className="absolute -left-6 -top-3 [transform:translateZ(50px)]">
                    <div className="surface-3d flex animate-float items-center gap-1.5 rounded-full border border-border bg-surface-raised px-2.5 py-1 text-body-sm font-medium tabular-nums text-foreground shadow-depth-2 motion-reduce:animate-none">
                      <Clock className="h-3.5 w-3.5 text-primary" />
                      {duration}s
                    </div>
                  </div>
                  <div className="absolute -bottom-4 -right-8 [transform:translateZ(70px)]">
                    <div
                      className="surface-3d flex animate-float items-center gap-1.5 rounded-full border border-border bg-surface-raised px-2.5 py-1 text-body-sm font-medium text-foreground shadow-depth-2 motion-reduce:animate-none"
                      style={{ animationDelay: '-2s' }}
                    >
                      <Mic className="h-3.5 w-3.5 text-primary" />
                      {voiceLabel}
                    </div>
                  </div>
                </div>
              </Tilt>
            </div>

            <dl className="mt-6 divide-y divide-border rounded-md border border-border bg-background/40 text-body-sm shadow-well">
              {[
                { term: 'Idea', value: ideaStatus, done: ideaValid },
                { term: 'Duration', value: `${duration} seconds`, done: true },
                { term: 'Aspect ratio', value: `${aspectRatio} · ${ratioLabel}`, done: true },
                { term: 'Voice', value: voiceLabel, done: true },
              ].map(({ term, value, done }) => (
                <div key={term} className="flex items-center justify-between gap-3 px-3 py-2.5">
                  <dt className="flex items-center gap-2 text-muted-foreground">
                    <span
                      aria-hidden
                      className={cn(
                        'flex h-4 w-4 items-center justify-center rounded-full border',
                        done
                          ? 'bg-accent-gradient border-transparent text-white'
                          : 'border-border text-transparent'
                      )}
                    >
                      <Check className="h-2.5 w-2.5" strokeWidth={3.5} />
                    </span>
                    {term}
                  </dt>
                  <dd className={cn('text-right font-medium', !done && 'text-muted-foreground')}>
                    {value}
                  </dd>
                </div>
              ))}
            </dl>

            <Button
              size="lg"
              variant="gradient"
              className="mt-6 w-full"
              disabled={!canSubmit}
              onClick={handleSubmit}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating script…
                </>
              ) : (
                <>
                  Generate Script
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
            <p className="mt-3 text-center text-body-sm text-muted-foreground">
              Next, you review and edit the Urdu script before the video is made.
            </p>
          </Card>
        </aside>
      </div>
    </div>
  )
}
