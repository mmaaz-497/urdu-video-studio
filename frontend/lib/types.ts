export interface UsageSummary {
  videosUsedToday: number
  videoLimit: number
  scriptsUsedToday: number
  scriptLimit: number
  resetsAt: string
}

export interface StudentProfile {
  id: string
  email: string
  createdAt: string
  usage: UsageSummary
}

export type DurationSeconds = 5 | 10 | 15
export type AspectRatio = '16:9' | '9:16'
export type VoiceId = 'male' | 'female'

export interface Voice {
  id: VoiceId
  label: string
  previewUrl: string
}

/** One 5 s segment: what the video generator draws and what the voice says over it. */
export interface Scene {
  visualPrompt: string
  narrationUr: string
}

export interface GeneratedScript {
  correctedIdea: string
  title: string
  urduScript: string // narrations joined; display / backward compatibility only
  scenes: Scene[]
  wordCount: number
  wordLimit: number
  sceneWordLimit: number
}

export interface VideoDownload {
  url: string
  filename: string
  expiresInSeconds: number
}

export type VideoJobStatus =
  | 'queued'
  | 'preparing'
  | 'generating_scenes'
  | 'adding_voice'
  | 'finalizing'
  | 'ready'
  | 'failed'

export interface VideoJobSummary {
  id: string
  title: string
  thumbnailUrl: string | null
  status: VideoJobStatus
  durationSeconds: DurationSeconds
  aspectRatio: AspectRatio
  createdAt: string
}

export interface VideoJob extends VideoJobSummary {
  progressCurrentScene: number | null
  progressTotalScenes: number
  failureReason: string | null
  videoUrl: string | null
  urduScript: string
  correctedIdea: string
  voiceId: VoiceId
  completedAt: string | null
}

export interface VideoJobListItem extends VideoJobSummary {
  failureReason: string | null
  videoUrl: string | null
}

export interface VideoJobListResponse {
  items: VideoJobListItem[]
  nextCursor: string | null
}
