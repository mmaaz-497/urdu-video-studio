'use client'

import type { ChangeEvent } from 'react'

import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

export const IDEA_MIN_LENGTH = 10
export const IDEA_MAX_LENGTH = 500

export interface IdeaTextareaProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  id?: string
}

/** Idea input with a live 10–500 character counter (FR-005). */
export function IdeaTextarea({ value, onChange, disabled, id = 'idea' }: IdeaTextareaProps) {
  const isTooShort = value.length > 0 && value.length < IDEA_MIN_LENGTH
  const isTooLong = value.length > IDEA_MAX_LENGTH
  const isInvalid = isTooShort || isTooLong

  function handleChange(event: ChangeEvent<HTMLTextAreaElement>) {
    onChange(event.target.value)
  }

  return (
    <div className="space-y-2">
      <Textarea
        id={id}
        value={value}
        onChange={handleChange}
        disabled={disabled}
        maxLength={IDEA_MAX_LENGTH}
        rows={5}
        aria-invalid={isInvalid}
        placeholder="اپنا آئیڈیا یہاں لکھیں — جیسے: Photosynthesis is how plants make their own food from sunlight"
        className={cn(
          'resize-none text-body',
          isInvalid && 'border-destructive focus-visible:ring-destructive'
        )}
      />
      <div className="flex items-center justify-between gap-3 text-body-sm">
        <span className={cn('text-muted-foreground', isInvalid && 'text-destructive')}>
          {isTooShort
            ? `Write at least ${IDEA_MIN_LENGTH} characters`
            : isTooLong
              ? 'Too long — please shorten your idea'
              : 'Roman Urdu, Urdu, or English — spelling mistakes are fine'}
        </span>
        <span className={cn('tabular-nums text-muted-foreground', isInvalid && 'text-destructive')}>
          {value.length}/{IDEA_MAX_LENGTH}
        </span>
      </div>
      <div aria-hidden className="h-1.5 overflow-hidden rounded-full bg-background shadow-well">
        <div
          className={cn(
            'h-full rounded-full transition-[width] duration-250 ease-out',
            isInvalid ? 'bg-destructive' : 'bg-accent-gradient'
          )}
          style={{ width: `${Math.min(100, (value.length / IDEA_MAX_LENGTH) * 100)}%` }}
        />
      </div>
    </div>
  )
}
