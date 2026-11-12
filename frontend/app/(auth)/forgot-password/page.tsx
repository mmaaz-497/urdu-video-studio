'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import Link from 'next/link'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { ApiError, apiClient } from '@/lib/api-client'

const forgotSchema = z.object({
  email: z.string().email('Enter a valid email address.'),
})

type ForgotValues = z.infer<typeof forgotSchema>

export default function ForgotPasswordPage() {
  const [submitting, setSubmitting] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  const form = useForm<ForgotValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: '' },
  })

  async function onSubmit(values: ForgotValues) {
    setSubmitting(true)
    try {
      await apiClient.post('/auth/forgot-password', values)
      setSubmittedEmail(values.email)
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  if (submittedEmail) {
    return (
      <Card className="w-full max-w-md animate-rise-in shadow-depth-3">
        <CardHeader className="space-y-1">
          <CardTitle className="text-h2">Check your email</CardTitle>
          <CardDescription>
            If an account exists for{' '}
            <span className="break-all font-medium text-foreground">{submittedEmail}</span>, we&apos;ve
            sent a link to reset your password. It expires in 30 minutes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-body-sm text-muted-foreground">
            <Link href="/login" className="font-medium text-foreground hover:underline">
              Back to log in
            </Link>
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md animate-rise-in shadow-depth-3">
      <CardHeader className="space-y-1">
        <CardTitle className="text-h2">Forgot your password?</CardTitle>
        <CardDescription>
          Enter your email and we&apos;ll send you a link to choose a new one.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="you@example.com" autoComplete="email" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" variant="gradient" className="w-full" disabled={submitting}>
              {submitting ? 'Sending…' : 'Send reset link'}
            </Button>
          </form>
        </Form>

        <p className="mt-6 text-center text-body-sm text-muted-foreground">
          Remembered it?{' '}
          <Link href="/login" className="font-medium text-foreground hover:underline">
            Log in
          </Link>
        </p>
      </CardContent>
    </Card>
  )
}
