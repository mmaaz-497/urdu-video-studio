'use client'

import { Pause, Play } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { IdeaTextarea, IDEA_MAX_LENGTH, IDEA_MIN_LENGTH } from '@/components/studio/idea-textarea'
import { AspectRatioShape, OptionCard } from '@/components/studio/option-card'
import { UsageBadge } from '@/components/studio/usage-badge'
import { Button } from '@/components/ui/button'
import { ApiError, apiClient } from '@/lib/api-client'
import { writeDraft, type ReviewDraft } from '@/lib/review-draft'
import { formatResetTime, useUsage } from '@/lib/use-usage'
import type { AspectRatio, DurationSeconds, GeneratedScript, Voice, VoiceId } from '@/lib/types'

const DURATIONS: DurationSeconds[] = [5, 10, 15]
const ASPECT_RATIOS: { value: AspectRatio; sublabel: string }[] = [
  { value: '16:9', sublabel: 'Landscape' },
  { value: '9:16', sublabel: 'Portrait' },
]

export default function CreatePage() {
  const router = useRouter()
  const [idea, setIdea] = useState('')
  const [duration, setDuration] = useState<DurationSeconds>(10)
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9')
  const [voiceId, setVoiceId] = useState<VoiceId>('female')
  const [voices, setVoices] = useState<Voice[]>([])
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
    <div className="mx-auto max-w-3xl space-y-10">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-h1 font-semibold">Create a video</h1>
          <UsageBadge />
        </div>
        <p className="text-body text-muted-foreground">
          Describe your idea, pick a style, and we&apos;ll turn it into a short Urdu script to
          review.
        </p>
      </div>

      {limitReached && profile && (
        <div className="rounded-md border border-warning/40 bg-warning/10 p-4 text-body text-warning">
          You&apos;ve used all your videos for today. Come back after midnight (Asia/Karachi) —
          resets {formatResetTime(profile.usage.resetsAt)}.
        </div>
      )}

      <section className="space-y-3">
        <label htmlFor="idea" className="text-h3 font-semibold">
          Your idea
        </label>
        <IdeaTextarea value={idea} onChange={setIdea} disabled={submitting} />
      </section>

      <section className="space-y-3" role="radiogroup" aria-label="Duration">
        <h2 className="text-h3 font-semibold">Duration</h2>
        <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-3 sm:overflow-visible sm:px-0">
          {DURATIONS.map((value) => (
            <OptionCard
              key={value}
              selected={duration === value}
              onSelect={() => setDuration(value)}
              disabled={submitting}
              label={`${value}s`}
            />
          ))}
        </div>
      </section>

      <section className="space-y-3" role="radiogroup" aria-label="Aspect ratio">
        <h2 className="text-h3 font-semibold">Aspect ratio</h2>
        <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0">
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
      </section>

      <section className="space-y-3" role="radiogroup" aria-label="Voice">
        <h2 className="text-h3 font-semibold">Voice</h2>
        <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0">
          {voices.map((voice) => (
            <OptionCard
              key={voice.id}
              selected={voiceId === voice.id}
              onSelect={() => setVoiceId(voice.id)}
              disabled={submitting}
              label={voice.label}
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
                  className="flex h-7 w-7 items-center justify-center rounded-full border border-border bg-background/80 text-foreground transition-colors hover:border-primary"
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
      </section>

      <Button
        size="lg"
        className="w-full bg-accent-gradient text-white hover:opacity-90 sm:w-auto"
        disabled={!canSubmit}
        onClick={handleSubmit}
      >
        {submitting ? 'Generating script…' : 'Generate Script'}
      </Button>
    </div>
  )
}
