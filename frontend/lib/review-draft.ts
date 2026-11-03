import type { AspectRatio, DurationSeconds, GeneratedScript, VoiceId } from '@/lib/types'

export const DRAFT_STORAGE_KEY = 'uvs:review-draft'

export interface ReviewDraft extends GeneratedScript {
  idea: string
  durationSeconds: DurationSeconds
  aspectRatio: AspectRatio
  voiceId: VoiceId
}

export function readDraft(): ReviewDraft | null {
  if (typeof window === 'undefined') return null
  const raw = sessionStorage.getItem(DRAFT_STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as ReviewDraft
  } catch {
    return null
  }
}

export function writeDraft(draft: ReviewDraft): void {
  sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft))
}

export function clearDraft(): void {
  sessionStorage.removeItem(DRAFT_STORAGE_KEY)
}
