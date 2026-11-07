'use client'

import { Download, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button, type ButtonProps } from '@/components/ui/button'
import { ApiError, apiClient } from '@/lib/api-client'
import type { VideoDownload } from '@/lib/types'

export interface DownloadButtonProps extends Omit<ButtonProps, 'onClick' | 'asChild'> {
  videoId: string
  label?: string
}

/** Saves a finished video as a file. `<a download>` is ignored for cross-origin URLs (the R2
 * link), which made the browser navigate to the raw MP4 and open its built-in player. Instead we
 * ask the backend (owner-only) for a short-lived URL whose response is `Content-Disposition:
 * attachment`, then follow it from a detached anchor — so nothing on the page, including the
 * player, is touched. */
export function DownloadButton({ videoId, label, children, disabled, ...props }: DownloadButtonProps) {
  const [busy, setBusy] = useState(false)

  async function handleClick(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (busy) return
    setBusy(true)
    try {
      const { url, filename } = await apiClient.get<VideoDownload>(`/videos/${videoId}/download`)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      anchor.rel = 'noopener'
      anchor.style.display = 'none'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : 'Could not start the download. Please try again.'
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <Button
      type="button"
      onClick={handleClick}
      disabled={disabled || busy}
      aria-label={label}
      {...props}
    >
      {busy ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Download className="h-4 w-4" />}
      {children}
    </Button>
  )
}
