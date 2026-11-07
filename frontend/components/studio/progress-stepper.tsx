import { Check } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { VideoJobStatus } from '@/lib/types'

export interface ProgressStepperProps {
  status: VideoJobStatus
  currentScene?: number | null
  totalScenes: number
  className?: string
}

interface Step {
  key: Exclude<VideoJobStatus, 'queued' | 'failed'>
  label: string
}

const STEPS: Step[] = [
  { key: 'preparing', label: 'Preparing' },
  { key: 'generating_scenes', label: 'Generating scenes' },
  { key: 'adding_voice', label: 'Adding voice' },
  { key: 'finalizing', label: 'Finalizing' },
  { key: 'ready', label: 'Ready' },
]

/** Horizontal (desktop) / vertical (mobile) step list: Preparing →
 * Generating scene i/N → Adding voice → Finalizing → Ready
 * (design-system.md Progress Stepper). `queued` is shown as "Preparing"
 * since mock-mode jobs pass through it almost instantly. */
export function ProgressStepper({ status, currentScene, totalScenes, className }: ProgressStepperProps) {
  const normalizedStatus = status === 'queued' ? 'preparing' : status
  const activeIndex = STEPS.findIndex((step) => step.key === normalizedStatus)

  return (
    <ol className={cn('flex flex-col gap-4 md:flex-row md:items-start md:gap-0', className)}>
      {STEPS.map((step, index) => {
        const isDone = index < activeIndex
        const isActive = index === activeIndex
        // currentScene === null while active means RunPod has the job queued (no GPU yet).
        const waitingForGpu = step.key === 'generating_scenes' && isActive && currentScene == null
        const label = waitingForGpu
          ? 'Waiting for a GPU…'
          : step.key === 'generating_scenes' && (isActive || isDone)
            ? `Generating scene ${Math.min(currentScene ?? 1, totalScenes) || 1}/${totalScenes}`
            : step.label

        return (
          <li key={step.key} className="flex flex-1 items-center gap-3 md:flex-col md:items-stretch md:gap-0">
            <div className="flex items-center gap-3 md:flex-col md:gap-2">
              <span
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-body-sm font-semibold transition-colors duration-250',
                  isDone && 'border-primary bg-primary text-primary-foreground',
                  isActive && 'border-primary bg-surface-raised text-primary animate-pulse motion-reduce:animate-none',
                  !isDone && !isActive && 'border-border bg-surface text-muted-foreground'
                )}
              >
                {isDone ? <Check className="h-4 w-4" /> : index + 1}
              </span>
              <span
                className={cn(
                  'text-body-sm font-medium md:text-center',
                  isDone || isActive ? 'text-foreground' : 'text-muted-foreground'
                )}
              >
                {label}
              </span>
            </div>
            {index < STEPS.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  'hidden h-px flex-1 bg-border md:mx-2 md:mt-4 md:block',
                  isDone && 'bg-primary'
                )}
              />
            )}
          </li>
        )
      })}
    </ol>
  )
}
