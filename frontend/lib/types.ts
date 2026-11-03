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
