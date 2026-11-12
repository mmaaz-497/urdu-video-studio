'use client'

import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { toast } from 'sonner'

import { VideoCard } from '@/components/studio/video-card'
import { Button } from '@/components/ui/button'
import { ApiError, apiClient } from '@/lib/api-client'
import type { VideoJob, VideoJobListResponse } from '@/lib/types'

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export default function MyVideosPage() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useInfiniteQuery<VideoJobListResponse, ApiError>({
      queryKey: ['videos'],
      queryFn: ({ pageParam }) =>
        apiClient.get<VideoJobListResponse>(
          pageParam ? `/videos?cursor=${encodeURIComponent(pageParam as string)}` : '/videos'
        ),
      initialPageParam: null as string | null,
      getNextPageParam: (lastPage) => lastPage.nextCursor,
    })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/videos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      toast.success('Video deleted.')
    },
    onError: (error) => toast.error(errorMessage(error, 'Could not delete this video. Please try again.')),
  })

  const retryMutation = useMutation({
    mutationFn: (id: string) => apiClient.post<VideoJob>(`/videos/${id}/retry`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      toast.success('Retrying — your video is back in the queue.')
    },
    onError: (error) => toast.error(errorMessage(error, 'Could not retry this video. Please try again.')),
  })

  const videos = data?.pages.flatMap((page) => page.items) ?? []

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-h1 font-semibold">My Videos</h1>
        <p className="text-body text-muted-foreground">Everything you&apos;ve created, newest first.</p>
      </div>

      {isLoading && (
        <div className="flex min-h-[30vh] items-center justify-center text-muted-foreground">
          Loading…
        </div>
      )}

      {isError && !isLoading && (
        <div className="flex min-h-[30vh] flex-col items-center justify-center gap-3 text-center">
          <p className="text-body text-muted-foreground">Could not load your videos. Please try again.</p>
        </div>
      )}

      {!isLoading && !isError && videos.length === 0 && (
        <div className="flex min-h-[30vh] flex-col items-center justify-center gap-4 text-center">
          <p className="text-body text-muted-foreground">
            You haven&apos;t created any videos yet.
          </p>
          <Button asChild variant="gradient">
            <Link href="/create">Create your first video</Link>
          </Button>
        </div>
      )}

      {videos.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {videos.map((job) => (
            <VideoCard
              key={job.id}
              job={job}
              onDelete={(id) => deleteMutation.mutate(id)}
              onRetry={(id) => retryMutation.mutate(id)}
              deleting={deleteMutation.isPending && deleteMutation.variables === job.id}
              retrying={retryMutation.isPending && retryMutation.variables === job.id}
            />
          ))}
        </div>
      )}

      {hasNextPage && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? 'Loading…' : 'Load more'}
          </Button>
        </div>
      )}
    </div>
  )
}
