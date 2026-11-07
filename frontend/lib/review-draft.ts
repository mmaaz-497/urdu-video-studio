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
    const draft = JSON.parse(raw) as ReviewDraft
    // A draft saved before per-scene narration holds scenes as plain strings: unusable.
    const valid = Array.isArray(draft.scenes) && draft.scenes.every((s) => typeof s === 'object' && s !== null)
    return valid ? draft : null
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
