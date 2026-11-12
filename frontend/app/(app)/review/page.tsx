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
import { formatResetTime, useUsage } from '@/lib/use-usage'
import type { GeneratedScript, Scene, VideoJob } from '@/lib/types'

function wordCount(text: string): number {
  const trimmed = text.trim()
  return trimmed.length === 0 ? 0 : trimmed.split(/\s+/).length
}

export default function ReviewPage() {
  const router = useRouter()
  const [draft, setDraft] = useState<ReviewDraft | null>(null)
  const [title, setTitle] = useState('')
  const [correctedIdea, setCorrectedIdea] = useState('')
  const [scenes, setScenes] = useState<Scene[]>([])
  const [sceneWordLimit, setSceneWordLimit] = useState(0)
  const [regenerating, setRegenerating] = useState(false)
  const [approving, setApproving] = useState(false)
  const { data: profile } = useUsage()
  const limitReached = profile ? profile.usage.videosUsedToday >= profile.usage.videoLimit : false

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
    setScenes(stored.scenes)
    setSceneWordLimit(stored.sceneWordLimit)
  }, [router])

  // Each scene is spoken over its own 5 s clip, so the limit and the gate are per scene.
  const sceneCounts = scenes.map((scene) => wordCount(scene.narrationUr))
  const totalWords = sceneCounts.reduce((sum, n) => sum + n, 0)
  const sceneProblem = scenes.some(
    (scene, i) =>
      sceneCounts[i] === 0 || sceneCounts[i] > sceneWordLimit || scene.visualPrompt.trim() === ''
  )
  const busy = regenerating || approving

  function updateScene(index: number, patch: Partial<Scene>) {
    setScenes((prev) => prev.map((scene, i) => (i === index ? { ...scene, ...patch } : scene)))
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
      setScenes(script.scenes)
      setSceneWordLimit(script.sceneWordLimit)
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
    if (!draft || sceneProblem || busy || limitReached) return
    setApproving(true)
    const idempotencyKey = crypto.randomUUID()
    try {
      const job = await apiClient.post<VideoJob>('/videos', {
        idempotencyKey,
        correctedIdea,
        title,
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

      <section className="space-y-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-h3 font-semibold">Scenes</h3>
            <span className="text-body-sm text-muted-foreground tabular-nums">
              {totalWords} words in total
            </span>
          </div>
          <p className="text-body-sm text-muted-foreground">
            Each scene is 5 seconds. The narration is spoken over its own scene, so keep the picture
            and the words about the same thing.
          </p>
        </div>
        <div className="space-y-4">
          {scenes.map((scene, index) => (
            <div
              key={index}
              data-testid="scene-card"
              className="surface-3d space-y-3 rounded-md border border-border bg-surface p-4 shadow-depth-2"
            >
              <span className="text-body-sm font-semibold text-muted-foreground">
                Scene {index + 1}
              </span>
              <div className="space-y-1">
                <label
                  className="text-body-sm font-medium text-muted-foreground"
                  htmlFor={`visual-${index}`}
                >
                  What you will see (English)
                </label>
                <Textarea
                  id={`visual-${index}`}
                  value={scene.visualPrompt}
                  onChange={(event) => updateScene(index, { visualPrompt: event.target.value })}
                  disabled={busy}
                  rows={2}
                  className="resize-none"
                />
              </div>
              <div className="space-y-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <label
                    className="text-body-sm font-medium text-muted-foreground"
                    htmlFor={`narration-${index}`}
                  >
                    What you will hear (Urdu)
                  </label>
                  <WordCounter count={sceneCounts[index]} limit={sceneWordLimit} />
                </div>
                <Textarea
                  id={`narration-${index}`}
                  value={scene.narrationUr}
                  onChange={(event) => updateScene(index, { narrationUr: event.target.value })}
                  disabled={busy}
                  rows={2}
                  dir="rtl"
                  className="urdu resize-none"
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {limitReached && profile && (
        <div className="rounded-md border border-warning/40 bg-warning/10 p-4 text-body text-warning shadow-depth-1">
          You&apos;ve used all your videos for today. Come back after midnight (Asia/Karachi) —
          resets {formatResetTime(profile.usage.resetsAt)}.
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button variant="outline" onClick={handleRegenerate} disabled={busy} className="sm:flex-1">
          {regenerating ? 'Regenerating…' : 'Regenerate'}
        </Button>
        <Button
          onClick={handleApprove}
          disabled={busy || sceneProblem || limitReached}
          variant="gradient"
          className="sm:flex-1"
        >
          {approving ? 'Creating video…' : 'Approve & Create Video'}
        </Button>
      </div>
    </div>
  )
}
