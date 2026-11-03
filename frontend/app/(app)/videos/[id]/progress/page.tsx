'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Download } from 'lucide-react'
import Link from 'next/link'
import { use, useEffect } from 'react'
import { toast } from 'sonner'

import { ProgressStepper } from '@/components/studio/progress-stepper'
import { Button } from '@/components/ui/button'
import { ApiError, apiClient } from '@/lib/api-client'
import type { VideoJob } from '@/lib/types'

export default function VideoProgressPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  const {
    data: job,
    error,
    isLoading,
  } = useQuery<VideoJob, ApiError>({
    queryKey: ['video-job', id],
    queryFn: () => apiClient.get<VideoJob>(`/videos/${id}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'ready' || status === 'failed' ? false : 3000
    },
  })

  useEffect(() => {
    if (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not load this video.')
    }
  }, [error])

  if (isLoading && !job) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-muted-foreground">
        Loading…
      </div>
    )
  }

  if (!job) {
    return (
      <div className="mx-auto max-w-xl space-y-4 text-center">
        <p className="text-body text-muted-foreground">We couldn&apos;t find this video.</p>
        <Button asChild className="bg-accent-gradient text-white hover:opacity-90">
          <Link href="/create">Back to Create</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="space-y-2 text-center">
        <h1 className="urdu text-h1 font-semibold" dir="rtl">
          {job.title}
        </h1>
        <p className="text-body text-muted-foreground">
          {job.status === 'ready'
            ? 'Your video is ready.'
            : job.status === 'failed'
              ? 'Something went wrong.'
              : "We're putting your video together — this usually takes a minute."}
        </p>
      </div>

      {job.status === 'failed' ? (
        <div className="flex flex-col items-center gap-4 rounded-md border border-destructive/30 bg-destructive/5 p-8 text-center">
          <AlertTriangle className="h-8 w-8 text-destructive" />
          <p className="text-body text-foreground">
            {job.failureReason ?? 'This video could not be created. Please try again.'}
          </p>
          <Button asChild className="bg-accent-gradient text-white hover:opacity-90">
            <Link href="/create">Start a new video</Link>
          </Button>
        </div>
      ) : (
        <div className="rounded-md border border-border bg-surface p-6 shadow-raised">
          <ProgressStepper
            status={job.status}
            currentScene={job.progressCurrentScene}
            totalScenes={job.progressTotalScenes}
          />
        </div>
      )}

      {job.status === 'ready' && job.videoUrl && (
        <div className="space-y-4">
          <div
            className={
              job.aspectRatio === '9:16'
                ? 'mx-auto aspect-[9/16] max-w-xs overflow-hidden rounded-lg border border-border bg-black shadow-raised'
                : 'mx-auto aspect-video max-w-xl overflow-hidden rounded-lg border border-border bg-black shadow-raised'
            }
          >
            <video
              src={job.videoUrl}
              controls
              className="h-full w-full"
              poster={job.thumbnailUrl ?? undefined}
            />
          </div>
          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild className="bg-accent-gradient text-white hover:opacity-90">
              <a href={job.videoUrl} download>
                <Download className="mr-2 h-4 w-4" />
                Download
              </a>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/create">Create another</Link>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
