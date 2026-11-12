'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { ApiError, apiClient } from '@/lib/api-client'

const resetSchema = z
  .object({
    newPassword: z.string().min(8, 'Password must be at least 8 characters.'),
    confirmPassword: z.string(),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: 'Passwords do not match.',
    path: ['confirmPassword'],
  })

type ResetValues = z.infer<typeof resetSchema>

function InvalidLinkCard() {
  return (
    <Card className="w-full max-w-md animate-rise-in shadow-depth-3">
      <CardHeader className="space-y-1">
        <CardTitle className="text-h2">This link can&apos;t be used</CardTitle>
        <CardDescription>
          This reset link is invalid, has expired, or has already been used. Request a new one to
          continue.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button asChild variant="gradient" className="w-full">
          <Link href="/forgot-password">Request a new link</Link>
        </Button>
        <p className="text-center text-body-sm text-muted-foreground">
          <Link href="/login" className="font-medium text-foreground hover:underline">
            Back to log in
          </Link>
        </p>
      </CardContent>
    </Card>
  )
}

function ResetPasswordForm() {
  const router = useRouter()
  const token = useSearchParams().get('token')
  const [submitting, setSubmitting] = useState(false)
  const [linkInvalid, setLinkInvalid] = useState(false)

  const form = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { newPassword: '', confirmPassword: '' },
  })

  if (!token || linkInvalid) {
    return <InvalidLinkCard />
  }

  async function onSubmit(values: ResetValues) {
    setSubmitting(true)
    try {
      await apiClient.post('/auth/reset-password', { token, newPassword: values.newPassword })
      toast.success('Password updated. Please log in with your new password.')
      router.push('/login')
    } catch (error) {
      if (error instanceof ApiError && error.code === 'INVALID_RESET_TOKEN') {
        setLinkInvalid(true)
      } else {
        const message =
          error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'
        toast.error(message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="w-full max-w-md animate-rise-in shadow-depth-3">
      <CardHeader className="space-y-1">
        <CardTitle className="text-h2">Choose a new password</CardTitle>
        <CardDescription>Use at least 8 characters.</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="newPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New password</FormLabel>
                  <FormControl>
                    <Input type="password" autoComplete="new-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirmPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm new password</FormLabel>
                  <FormControl>
                    <Input type="password" autoComplete="new-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" variant="gradient" className="w-full" disabled={submitting}>
              {submitting ? 'Updating…' : 'Update password'}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  )
}
