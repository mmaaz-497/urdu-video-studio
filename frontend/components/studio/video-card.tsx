'use client'

import { AlertTriangle, Loader2, Play, RotateCcw, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { useRef, useState } from 'react'

import { DownloadButton } from '@/components/studio/download-button'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { VideoJobListItem } from '@/lib/types'

export interface VideoCardProps {
  job: VideoJobListItem
  onDelete: (id: string) => void
  onRetry: (id: string) => void
  deleting?: boolean
  retrying?: boolean
  className?: string
}

const STATUS_LABEL: Record<VideoJobListItem['status'], string> = {
  queued: 'Processing',
  preparing: 'Processing',
  generating_scenes: 'Processing',
  adding_voice: 'Processing',
  finalizing: 'Processing',
  ready: 'Ready',
  failed: 'Failed',
}

const STATUS_BADGE_CLASS: Record<VideoJobListItem['status'], string> = {
  queued: 'border-warning/40 bg-warning/10 text-warning',
  preparing: 'border-warning/40 bg-warning/10 text-warning',
  generating_scenes: 'border-warning/40 bg-warning/10 text-warning',
  adding_voice: 'border-warning/40 bg-warning/10 text-warning',
  finalizing: 'border-warning/40 bg-warning/10 text-warning',
  ready: 'border-success/40 bg-success/10 text-success',
  failed: 'border-destructive/40 bg-destructive/10 text-destructive',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

/** My Videos grid card (design-system.md "Video Card"): thumbnail with
 * hover-autoplay preview, status badge, metadata, and play/download/
 * delete/retry actions gated by job status. */
export function VideoCard({ job, onDelete, onRetry, deleting, retrying, className }: VideoCardProps) {
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const isReady = job.status === 'ready'
  const isFailed = job.status === 'failed'
  const isProcessing = !isReady && !isFailed

  function handleMouseEnter() {
    if (isReady && job.videoUrl) {
      videoRef.current?.play().catch(() => {})
    }
  }

  function handleMouseLeave() {
    if (videoRef.current) {
      videoRef.current.pause()
      videoRef.current.currentTime = 0
    }
  }

  function handleDeleteClick() {
    if (!confirmingDelete) {
      setConfirmingDelete(true)
      return
    }
    setConfirmingDelete(false)
    onDelete(job.id)
  }

  return (
    <div
      className={cn(
        'group flex flex-col overflow-hidden rounded-md border border-border bg-surface shadow-raised transition-colors',
        className
      )}
    >
      <Link
        href={`/videos/${job.id}/progress`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className={cn(
          'relative block bg-black',
          job.aspectRatio === '9:16' ? 'aspect-[9/16]' : 'aspect-video'
        )}
      >
        {isReady && job.videoUrl ? (
          <video
            ref={videoRef}
            src={job.videoUrl}
            poster={job.thumbnailUrl ?? undefined}
            muted
            loop
            playsInline
            preload="none"
            className="h-full w-full object-cover"
          />
        ) : job.thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={job.thumbnailUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            {isProcessing ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground motion-reduce:animate-none" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-destructive" />
            )}
          </div>
        )}

        <span
          className={cn(
            'absolute left-2 top-2 inline-flex items-center rounded-full border px-2 py-0.5 text-body-sm font-medium backdrop-blur',
            STATUS_BADGE_CLASS[job.status]
          )}
        >
          {STATUS_LABEL[job.status]}
        </span>
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="urdu truncate text-h3 font-semibold" dir="rtl" title={job.title}>
          {job.title}
        </h3>
        <p className="text-body-sm text-muted-foreground">
          {formatDate(job.createdAt)} · {job.durationSeconds}s · {job.aspectRatio}
        </p>

        {isFailed && (
          <p className="text-body-sm text-destructive">
            {job.failureReason ?? 'This video could not be created.'}
          </p>
        )}

        <div className="mt-auto flex items-center gap-2 pt-2">
          {isReady && (
            <>
              <Button variant="outline" size="icon" asChild aria-label="Play video">
                <Link href={`/videos/${job.id}/progress`}>
                  <Play className="h-4 w-4" />
                </Link>
              </Button>
              {job.videoUrl && (
                <DownloadButton
                  videoId={job.id}
                  variant="outline"
                  size="icon"
                  label="Download video"
                />
              )}
            </>
          )}

          {isFailed && (
            <Button
              variant="outline"
              size="icon"
              aria-label="Retry video"
              disabled={retrying}
              onClick={() => onRetry(job.id)}
            >
              <RotateCcw className={cn('h-4 w-4', retrying && 'animate-spin motion-reduce:animate-none')} />
            </Button>
          )}

          {(isReady || isFailed) && (
            <Button
              variant={confirmingDelete ? 'destructive' : 'outline'}
              size={confirmingDelete ? 'sm' : 'icon'}
              aria-label="Delete video"
              disabled={deleting}
              onClick={handleDeleteClick}
              onBlur={() => setConfirmingDelete(false)}
              className="ml-auto"
            >
              <Trash2 className="h-4 w-4" />
              {confirmingDelete && <span className="ml-1">Confirm?</span>}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
