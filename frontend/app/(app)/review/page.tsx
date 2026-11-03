'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { WordCounter } from '@/components/studio/word-counter'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, apiClient } from '@/lib/api-client'
import { clearDraft, readDraft, writeDraft, type ReviewDraft } from '@/lib/review-draft'
import type { GeneratedScript, VideoJob } from '@/lib/types'

function wordCount(text: string): number {
  const trimmed = text.trim()
  return trimmed.length === 0 ? 0 : trimmed.split(/\s+/).length
}

export default function ReviewPage() {
  const router = useRouter()
  const [draft, setDraft] = useState<ReviewDraft | null>(null)
  const [title, setTitle] = useState('')
  const [correctedIdea, setCorrectedIdea] = useState('')
  const [urduScript, setUrduScript] = useState('')
  const [scenes, setScenes] = useState<string[]>([])
  const [wordLimit, setWordLimit] = useState(0)
  const [regenerating, setRegenerating] = useState(false)
  const [approving, setApproving] = useState(false)

  useEffect(() => {
    const stored = readDraft()
    if (!stored) {
      toast.error('Start by describing your idea on the Create page.')
      router.replace('/create')
      return
    }
    setDraft(stored)
    setTitle(stored.title)
    setCorrectedIdea(stored.correctedIdea)
    setUrduScript(stored.urduScript)
    setScenes(stored.scenes)
    setWordLimit(stored.wordLimit)
  }, [router])

  const currentWordCount = wordCount(urduScript)
  const overLimit = currentWordCount > wordLimit
  const busy = regenerating || approving

  function updateScene(index: number, value: string) {
    setScenes((prev) => prev.map((scene, i) => (i === index ? value : scene)))
  }

  async function handleRegenerate() {
    if (!draft || busy) return
    setRegenerating(true)
    const idempotencyKey = crypto.randomUUID()
    try {
      const script = await apiClient.post<GeneratedScript>('/scripts', {
        idempotencyKey,
        idea: draft.idea,
        durationSeconds: draft.durationSeconds,
        aspectRatio: draft.aspectRatio,
        voiceId: draft.voiceId,
      })
      const nextDraft: ReviewDraft = { ...draft, ...script }
      writeDraft(nextDraft)
      setDraft(nextDraft)
      setTitle(script.title)
      setCorrectedIdea(script.correctedIdea)
      setUrduScript(script.urduScript)
      setScenes(script.scenes)
      setWordLimit(script.wordLimit)
      toast.success('Regenerated a fresh script.')
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Could not regenerate the script. Please try again.'
      toast.error(message)
    } finally {
      setRegenerating(false)
    }
  }

  async function handleApprove() {
    if (!draft || overLimit || busy) return
    setApproving(true)
    const idempotencyKey = crypto.randomUUID()
    try {
      const job = await apiClient.post<VideoJob>('/videos', {
        idempotencyKey,
        correctedIdea,
        title,
        urduScript,
        scenes,
        durationSeconds: draft.durationSeconds,
        aspectRatio: draft.aspectRatio,
        voiceId: draft.voiceId,
      })
      clearDraft()
      router.push(`/videos/${job.id}/progress`)
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Could not create the video. Please try again.'
      toast.error(message)
      setApproving(false)
    }
  }

  if (!draft) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-muted-foreground">
        Loading your script…
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="space-y-2">
        <h1 className="text-h1 font-semibold">Review your script</h1>
        <p className="text-body text-muted-foreground">
          Edit anything that doesn&apos;t sound right, then approve to start creating your video.
        </p>
      </div>

      <section className="space-y-2">
        <label className="text-h3 font-semibold" htmlFor="title">
          Title
        </label>
        <Input
          id="title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          disabled={busy}
          dir="rtl"
          className="urdu h-auto"
        />
      </section>

      <section className="space-y-2">
        <label className="text-h3 font-semibold" htmlFor="corrected-idea">
          Your idea (corrected)
        </label>
        <Textarea
          id="corrected-idea"
          value={correctedIdea}
          onChange={(event) => setCorrectedIdea(event.target.value)}
          disabled={busy}
          rows={3}
          dir="rtl"
          className="urdu resize-none"
        />
      </section>

      <section className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="text-h3 font-semibold" htmlFor="urdu-script">
            Narration script
          </label>
          <WordCounter count={currentWordCount} limit={wordLimit} />
        </div>
        <Textarea
          id="urdu-script"
          value={urduScript}
          onChange={(event) => setUrduScript(event.target.value)}
          disabled={busy}
          rows={6}
          dir="rtl"
          className="urdu resize-none"
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-h3 font-semibold">Scenes</h3>
        <div className="space-y-3">
          {scenes.map((scene, index) => (
            <div key={index} className="space-y-1">
              <span className="text-body-sm font-medium text-muted-foreground">
                Scene {index + 1}
              </span>
              <Textarea
                value={scene}
                onChange={(event) => updateScene(index, event.target.value)}
                disabled={busy}
                rows={2}
                className="resize-none"
              />
            </div>
          ))}
        </div>
      </section>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button variant="outline" onClick={handleRegenerate} disabled={busy} className="sm:flex-1">
          {regenerating ? 'Regenerating…' : 'Regenerate'}
        </Button>
        <Button
          onClick={handleApprove}
          disabled={busy || overLimit}
          className="bg-accent-gradient text-white hover:opacity-90 sm:flex-1"
        >
          {approving ? 'Creating video…' : 'Approve & Create Video'}
        </Button>
      </div>
    </div>
  )
}
